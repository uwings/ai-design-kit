"""设计校验器：5 类确定性校验 + 命名规则注册表。

校验类别：
  component — 节点引用的组件已注册（防 raw imitation）
  variant   — 变体取值在契约内
  slot      — slot 子组件合法、min/max 满足
  token     — 无硬编码颜色、token 引用存在
  graph/a11y— 命名规则函数（primary CTA 唯一、破坏性需确认、icon-only 需 aria 等）

每条 hardRule(hardRules/compositionRules) 若 kind=fn，expr 形如 "fn:<name>"，
由本文件 RULE_FNS 注册表查表执行；无对应函数的规则记为 unresolved（risky，诚实标注覆盖盲区）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional

from .contract import Contract, ContractIndex
from .graph import GraphNode, SemanticGraph
from .tokens import TokenGraph

_HEX_RGB_RE = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgb)")


@dataclass
class Issue:
    severity: str  # blocking | risky | improvement
    kind: str  # component | variant | slot | token | schema | graph | a11y
    message: str
    node: Optional[str] = None
    component: Optional[str] = None
    rule: Optional[str] = None
    fixOp: Optional[dict] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None or k in ("node",)}


@dataclass
class ValidationReport:
    passed: bool
    issues: List[Issue] = field(default_factory=list)
    counts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "counts": self.counts,
            "issues": [i.to_dict() for i in self.issues],
        }

    @property
    def blocking(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "blocking"]


def _is_hardcoded_color(v) -> bool:
    return isinstance(v, str) and bool(_HEX_RGB_RE.match(v.strip()))


def _eval_required_when(expr: str, node: GraphNode) -> bool:
    """极简 requiredWhen 求值：支持 'prop==value'、'prop!=value'、'iconOnly==true' 等单条件。"""
    if not expr:
        return True
    for op in ("==", "!="):
        if op in expr:
            left, right = [s.strip() for s in expr.split(op, 1)]
            actual = node.props.get(left)
            right_val = right.lower() in ("true", "false") and (right.lower() == "true") or right
            try:
                right_val = int(right)
            except (ValueError, TypeError):
                pass
            if op == "==":
                if actual != right_val:
                    return False
            else:
                if actual == right_val:
                    return False
            return True
    return True  # 无法解析的条件默认不触发


# ---------- 命名规则函数注册表 ----------

RuleFn = Callable[[GraphNode, Contract, SemanticGraph, ContractIndex, "Context"], List[Issue]]


def _rule_primary_max_one(node: GraphNode, c: Contract, g: SemanticGraph, idx: ContractIndex, ctx) -> List[Issue]:
    """一个 action group 内最多 1 个 primary button。按父节点分组统计。"""
    if c.id.split(".")[-1] != "button":
        return []
    issues: List[Issue] = []
    # 在整图中按父分组统计 primary button
    groups: Dict[str, List[GraphNode]] = {}
    for n, parent, slot in g.walk():
        if n.component == c.id and n.variant.get("intent") == "primary":
            key = parent.id if parent else "__root__"
            groups.setdefault(key, []).append(n)
    for key, btns in groups.items():
        if len(btns) > 1:
            for extra in btns[1:]:
                issues.append(Issue(
                    "blocking", "graph",
                    f"action group '{key}' has {len(btns)} primary buttons; max 1 allowed",
                    node=extra.id, component=extra.component, rule="primary_max_one_per_action_group",
                    fixOp={"op": "component.setVariant", "nodeId": extra.id,
                           "variant": {"intent": "secondary"}, "reason": "demote extra primary CTA"},
                ))
    return issues


def _rule_destructive_needs_confirmation(node: GraphNode, c: Contract, g: SemanticGraph, idx: ContractIndex, ctx) -> List[Issue]:
    """破坏性操作（button intent=danger）必须有确认 modal 存在于同一图。"""
    if not (c.id.split(".")[-1] == "button" and node.variant.get("intent") == "danger"):
        return []
    has_modal = any(n.component.endswith(".modal") for n in g.all_nodes())
    if not has_modal:
        return [Issue(
            "blocking", "graph",
            "destructive action present but no confirmation modal in page",
            node=node.id, component=node.component, rule="destructive_requires_confirmation",
            fixOp={"op": "component.insert", "componentId": "antd.modal",
                   "parentId": node.parent.id if node.parent else None,
                   "node": {"id": node.id + "-confirm", "variant": {"intent": "confirm"},
                            "props": {"title": "确认执行此操作？"}},
                   "reason": "add confirmation modal for destructive action"},
        )]
    return []


def _rule_icononly_aria(node: GraphNode, c: Contract, g: SemanticGraph, idx: ContractIndex, ctx) -> List[Issue]:
    if node.props.get("iconOnly") is True and not node.props.get("ariaLabel"):
        return [Issue(
            "blocking", "a11y", "icon-only button requires ariaLabel",
            node=node.id, component=node.component, rule="icon_only_requires_aria_label",
            fixOp={"op": "component.setProp", "nodeId": node.id, "prop": "ariaLabel",
                   "value": "describe action", "reason": "add accessible label"},
        )]
    return []


RULE_FNS: Dict[str, RuleFn] = {
    "primary_max_one_per_action_group": _rule_primary_max_one,
    "destructive_requires_confirmation": _rule_destructive_needs_confirmation,
    "icon_only_requires_aria_label": _rule_icononly_aria,
}


@dataclass
class Context:
    tg: Optional[TokenGraph] = None


def validate_graph(graph: SemanticGraph, idx: ContractIndex, tg: Optional[TokenGraph] = None,
                   run_named_rules: bool = True) -> ValidationReport:
    issues: List[Issue] = []
    ctx = Context(tg=tg)
    seen_rule_results: Dict[str, List[Issue]] = {}

    for node, parent, slot_name in graph.walk():
        c = idx.get(node.component)
        # 1) component
        if c is None:
            issues.append(Issue(
                "blocking", "component",
                f"unregistered component '{node.component}' — raw imitation not allowed",
                node=node.id, component=node.component,
            ))
            continue
        # 2) variant
        for axis, val in node.variant.items():
            allowed = c.variant_values(axis)
            if axis not in c.variants:
                issues.append(Issue("blocking", "variant",
                                    f"unknown variant axis '{axis}' on {c.id}", node=node.id, component=c.id))
            elif allowed and val not in allowed:
                issues.append(Issue("blocking", "variant",
                                    f"variant {axis}={val!r} not in {allowed}", node=node.id, component=c.id,
                                    rule=f"variant:{axis}",
                                    fixOp={"op": "component.setVariant", "nodeId": node.id,
                                           "variant": {axis: allowed[0]}, "reason": f"reset {axis} to valid value"}))
        # 3) props (schema-ish)
        cprops = c.props
        for pname, pval in node.props.items():
            pspec = cprops.get(pname)
            if pspec is None:
                # 允许 data-* / aria-* 等透传；其他未声明 prop 记 risky
                if not (pname.startswith("data-") or pname.startswith("aria")):
                    issues.append(Issue("risky", "schema",
                                        f"prop '{pname}' not declared on {c.id}", node=node.id, component=c.id))
                continue
            ptype = pspec.get("type")
            if ptype == "enum" and "enum" in pspec and pval not in pspec["enum"]:
                issues.append(Issue("blocking", "schema",
                                    f"prop {pname}={pval!r} not in enum {pspec['enum']}", node=node.id, component=c.id))
            if ptype == "string" and "maxLength" in pspec and isinstance(pval, str) and len(pval) > pspec["maxLength"]:
                issues.append(Issue("blocking", "schema",
                                    f"prop {pname} length {len(pval)} > maxLength {pspec['maxLength']}",
                                    node=node.id, component=c.id, rule=f"{pname}.maxLength"))
            if ptype == "number" and isinstance(pval, (int, float)):
                if "minimum" in pspec and pval < pspec["minimum"]:
                    issues.append(Issue("blocking", "schema", f"prop {pname} < minimum {pspec['minimum']}", node=node.id, component=c.id))
                if "maximum" in pspec and pval > pspec["maximum"]:
                    issues.append(Issue("blocking", "schema", f"prop {pname} > maximum {pspec['maximum']}", node=node.id, component=c.id))
        # required / requiredWhen
        for pname, pspec in cprops.items():
            if pspec.get("required") and pname not in node.props:
                issues.append(Issue("blocking", "schema", f"required prop '{pname}' missing on {c.id}",
                                    node=node.id, component=c.id, rule=f"{pname}.required"))
            elif pspec.get("requiredWhen") and _eval_required_when(pspec["requiredWhen"], node) and pname not in node.props:
                issues.append(Issue("blocking", "a11y", f"conditionally required prop '{pname}' missing ({pspec['requiredWhen']})",
                                    node=node.id, component=c.id))
        # 4) token
        for ppath, tref in node.token_refs.items():
            if tg and not tg.has(tref):
                issues.append(Issue("blocking", "token", f"token reference '{tref}' not found in token graph",
                                    node=node.id, component=c.id, rule="token.reference"))
        # 硬编码颜色扫描
        for pname, pval in node.props.items():
            if _is_hardcoded_color(pval):
                issues.append(Issue("blocking", "token",
                                    f"hardcoded color '{pval}' in prop '{pname}' — must reference a token",
                                    node=node.id, component=c.id, rule="no_hardcoded_color",
                                    fixOp={"op": "token.reference", "nodeId": node.id, "path": pname,
                                           "token": "color.brand.primary", "reason": "bind to semantic token"}))
        # 5) slot
        for sname, kids in node.slots.items():
            sc = c.slot_contract(sname)
            if not sc and sname not in c.slots:
                issues.append(Issue("blocking", "slot", f"unknown slot '{sname}' on {c.id}",
                                    node=node.id, component=c.id))
                continue
            accepts = sc.get("accepts", [])
            for k in kids:
                if accepts and k.component not in accepts:
                    issues.append(Issue("blocking", "slot",
                                        f"slot '{sname}' disallows component '{k.component}' (accepts {accepts})",
                                        node=k.id, component=k.component, rule=f"slot:{sname}.accepts"))
            if "max" in sc and len(kids) > sc["max"]:
                issues.append(Issue("blocking", "slot",
                                    f"slot '{sname}' has {len(kids)} children > max {sc['max']}",
                                    node=node.id, component=c.id, rule=f"slot:{sname}.max"))
            if "min" in sc and len(kids) < sc["min"]:
                issues.append(Issue("blocking", "slot",
                                    f"slot '{sname}' has {len(kids)} children < min {sc['min']}",
                                    node=node.id, component=c.id, rule=f"slot:{sname}.min"))
        # 6) 命名规则（hardRules kind=fn + compositionRules severity=hard）
        if run_named_rules:
            fns_to_run = []
            for hr in c.hard_rules:
                if hr.get("kind") == "fn" and hr.get("expr", "").startswith("fn:"):
                    fns_to_run.append((hr["expr"][3:].strip(), hr.get("id", hr["expr"])))
            for cr in c.composition_rules:
                if cr.get("severity") == "hard" and cr.get("assert", "").startswith("fn:"):
                    fns_to_run.append((cr["assert"][3:].strip(), cr.get("id", cr["assert"])))
            for fn_name, rule_id in fns_to_run:
                fn = RULE_FNS.get(fn_name)
                if fn is None:
                    issues.append(Issue("risky", "graph",
                                        f"unresolved named rule '{fn_name}' on {c.id} (no validator fn registered)",
                                        node=node.id, component=c.id, rule=rule_id))
                    continue
                results = seen_rule_results.setdefault(fn_name, [])
                if results:
                    continue  # 图级规则全图只跑一次（结果已收集）
                new_issues = fn(node, c, graph, idx, ctx)
                seen_rule_results[fn_name] = new_issues
                issues.extend(new_issues)

    counts = {"blocking": 0, "risky": 0, "improvement": 0}
    for i in issues:
        counts[i.severity] = counts.get(i.severity, 0) + 1
    return ValidationReport(passed=counts["blocking"] == 0, issues=issues, counts=counts)


def validate_ops(ops: List[dict], idx: ContractIndex, tg: Optional[TokenGraph] = None,
                 system: str = "ant-design") -> ValidationReport:
    """应用 ops 构图后校验。"""
    from .ops import apply_ops
    graph = apply_ops(ops, system=system)
    return validate_graph(graph, idx, tg)
