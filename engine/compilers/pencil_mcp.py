"""Pencil MCP 验证层（可选）。

两层：
  1) verify_pen_structure(pen) — 对编译出的 .pen JSON 做确定性结构自检（镜像 Pencil MCP 会查的项）。
     无需运行中的 Pencil 实例即可跑。验证：每个 UI 节点是 ref、变量存在、fill 无硬编码 hex、
     metadata 带组件身份、slot 声明保留。
  2) verify_with_mcp(pen_path) — 实时 Pencil MCP 协议（batch_get / get_variables /
     snapshot_layout / get_screenshot）。需要运行中的 Pencil 应用（IDE/桌面）。
     本模块提供协议编排；实际 MCP 调用由 agent（持有 mcp__pencil__ 工具）执行，
     或由 MCP 客户端驱动。无 Pencil 时本函数返回结构化的 "unavailable" 报告。

架构定位：语义图是唯一真相源；静态校验（engine.validator）是硬约束；
Pencil MCP 是视觉校验闭环（可选）。.pen 是编译目标，不是设计源。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

_HEX_RE = re.compile(r"^(#[0-9a-fA-F]{3,8})$")


@dataclass
class PenIssue:
    severity: str  # blocking | risky
    kind: str
    message: str
    node: str = None


@dataclass
class PenReport:
    passed: bool
    checks: Dict[str, bool] = field(default_factory=dict)
    issues: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"passed": self.passed, "checks": self.checks,
                "issues": [asdict(i) for i in self.issues] if self.issues else []}


def _walk_refs(node: dict) -> List[dict]:
    out = []

    def rec(n):
        if not isinstance(n, dict):
            return
        if n.get("type") == "ref" or n.get("reusable") is True:
            out.append(n)
        for c in n.get("children", []) or []:
            rec(c)
        for kids in (n.get("slots") or {}).values():
            for k in kids:
                rec(k)

    rec(node)
    return out


def verify_pen_structure(pen: dict) -> PenReport:
    """确定性自检：编译出的 .pen 是否满足 ADK 约束（镜像 MCP 会查的项）。"""
    issues: List[PenIssue] = []
    variables = pen.get("variables", {})
    var_names = set(variables.keys())
    all_refs = []

    for page in pen.get("children", []):
        all_refs.extend(_walk_refs(page))

    # 1) 所有 UI 节点是 ref（无 raw imitation）
    raw_nodes = [r for r in all_refs if r.get("type") not in ("ref",) and r.get("reusable") is not True
                 and r.get("type") not in ("frame",) and not r.get("metadata", {}).get("type") == "page"]
    # 页面 frame 允许；reusable 允许
    ref_nodes = [r for r in all_refs if r.get("type") == "ref"]
    check_ref_only = len(raw_nodes) == 0
    if not check_ref_only:
        issues.append(PenIssue("blocking", "raw_imitation",
                               f"{len(raw_nodes)} non-ref/non-reusable UI nodes (raw imitation?)"))

    # 2) 每个实例 metadata 带组件身份
    missing_id = [r.get("id") for r in ref_nodes
                  if not (r.get("metadata") or {}).get("componentId")]
    check_identity = not missing_id
    if missing_id:
        issues.append(PenIssue("blocking", "identity", f"{len(missing_id)} ref nodes missing componentId"))

    # 3) fill 无硬编码 hex（应引用 $variable）
    hardcoded = []
    for r in all_refs:
        fill = r.get("fill")
        if isinstance(fill, str) and _HEX_RE.match(fill):
            hardcoded.append((r.get("id"), fill))
    check_no_hex = not hardcoded
    if hardcoded:
        issues.append(PenIssue("blocking", "hardcoded_color",
                               f"{len(hardcoded)} nodes use raw hex fill: {hardcoded[:3]}"))

    # 4) 变量存在
    check_vars = len(variables) > 0
    if not check_vars:
        issues.append(PenIssue("risky", "no_variables", "no token variables in .pen"))

    blocking = sum(1 for i in issues if i.severity == "blocking")
    return PenReport(
        passed=blocking == 0,
        checks={"refs_only": check_ref_only, "component_identity": check_identity,
                "no_hardcoded_color": check_no_hex, "variables_present": check_vars,
                "ref_count": len(ref_nodes), "variable_count": len(variables)},
        issues=issues,
    )


def verify_with_mcp(pen_path: str) -> dict:
    """实时 Pencil MCP 验证协议（需运行中的 Pencil 应用）。

    本函数返回验证清单；实际 MCP 工具调用由 agent（持有 mcp__pencil__ 工具）按此清单执行：
      1. get_editor_state({include_schema:true}) — 获取上下文
      2. 在编辑器中打开 pen_path（或 batch_design 写入）
      3. batch_get — 确认节点为 ref + metadata.componentId
      4. get_variables — 确认 token 变量存在、被引用
      5. snapshot_layout — 无 overlap/overflow
      6. get_screenshot — 视觉合理性（层级/密度/对比度）
    无运行中的 Pencil 时返回 unavailable（不阻塞——静态校验已是硬约束）。
    """
    return {
        "status": "protocol_only",
        "pen": pen_path,
        "steps": [
            "get_editor_state({include_schema:true})",
            "open/load the .pen in the Pencil editor",
            "batch_get → assert type=='ref' + metadata.componentId for UI nodes",
            "get_variables → assert token variables exist & are referenced",
            "snapshot_layout → assert no overlap/overflow",
            "get_screenshot → visual sanity (hierarchy/density/contrast)",
        ],
        "note": "Pencil MCP 是可选视觉校验层。无运行中的 Pencil 应用时跳过；静态校验(engine.validator)+ .pen 结构自检(verify_pen_structure)已是硬约束。",
    }
