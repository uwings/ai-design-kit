"""语义图 → Pencil .pen JSON。

v1 产出**结构正确**的 Pencil IR（refs / descendants / variables / slots / metadata 齐全），
保证 validator 与 Pencil MCP 验证可读。完整逐组件视觉保真度（每个 AntD 组件的视觉树）
是后续扩展——lib 编译器架构支持为每个 contract 追加 visualTemplate。

Pencil 数据模型要点（来自架构圣经调研）：
  reusable:true      注册可复用组件
  type:"ref" + ref   实例引用
  descendants        覆盖组件内部子节点（path -> override）
  variables          token 化值，节点用 $name 引用
  slot               frame 上声明的可填充区域 + allowed 元组件
  metadata           组件身份（componentId/contractVersion/system/allowedOverrides/tokenBindings/slotContracts）
绝不编译 raw imitation 组件。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..contract import Contract, ContractIndex
from ..graph import GraphNode, SemanticGraph
from ..tokens import TokenGraph

PEN_VERSION = "2.13"


def _var_name(token_id: str) -> str:
    """token id -> Pencil 变量名（Pencil 用 $name 引用）。"""
    return token_id


def build_variables(tg: Optional[TokenGraph], mode: Optional[str] = None) -> Dict[str, Any]:
    """从 token 图生成 Pencil variables（按模式解析为最终值；含 theme axes）。"""
    variables: Dict[str, Any] = {}
    if tg is None:
        return variables
    use_mode = mode or tg.default_mode
    for tid, tok in tg.tokens.items():
        ptype = tok.get("type", "color")
        val = tg.resolve(tid, use_mode)
        # 对暗/亮都给一个值；Pencil 变量可带 theme。v1 写成扁平变量，值取当前模式
        variables[_var_name(tid)] = {"type": ptype, "value": val if val is not None else "#000000"}
    return variables


def _meta_for(c: Contract) -> Dict[str, Any]:
    return {
        "type": "design-system-component",
        "componentId": c.id,
        "contractVersion": c.version,
        "system": c.system,
        "allowedDescendantOverrides": c.pencil.get("allowedDescendantOverrides", {}),
        "tokenBindings": c.token_bindings,
        "slotContracts": c.slots,
        "variantAxes": list(c.variants.keys()),
    }


def compile_reusable(c: Contract, tg: Optional[TokenGraph]) -> Dict[str, Any]:
    """把单个契约编译为 Pencil 可复用组件（结构模板）。"""
    node: Dict[str, Any] = {
        "id": c.id,
        "type": c.pencil.get("rootNodeType", "frame"),
        "reusable": True,
        "layout": "vertical",
        "padding": 8,
        "metadata": _meta_for(c),
    }
    # token 化的根 fill：仅当 binding 是无占位符的具名 token 时绑定到变量
    root_fill_binding = c.token_bindings.get("root.fill")
    if root_fill_binding and "{" not in root_fill_binding and "}" not in root_fill_binding:
        node["fill"] = "$" + _var_name(root_fill_binding)
    # 主内容文本子节点（取第一个 string prop 作为可编辑内容，便于 descendants override）
    children: List[Dict[str, Any]] = []
    string_props = [n for n, p in c.props.items() if p.get("type") == "string"]
    if string_props:
        label_prop = string_props[0]
        text_node = {"id": "label", "type": "text", "content": c.display_name}
        label_fill_binding = c.token_bindings.get("label.fill")
        if label_fill_binding and "{" not in label_fill_binding and "}" not in label_fill_binding:
            text_node["fill"] = "$" + _var_name(label_fill_binding)
        children.append(text_node)
    # slot 区域
    for sname, sc in c.slots.items():
        children.append({
            "id": f"slot-{sname}", "type": "frame", "name": f"slot:{sname}",
            "slot": sc.get("accepts", []),
            "layout": sc.get("layout", "vertical"),
            "metadata": {"slotName": sname, "accepts": sc.get("accepts", []),
                         "min": sc.get("min", 0), "max": sc.get("max", 999)},
        })
    if children:
        node["children"] = children
    return node


def compile_library(idx: ContractIndex, tg: Optional[TokenGraph] = None) -> Dict[str, Any]:
    """编译整个体系的契约为 Pencil library（.lib.pen）。"""
    return {
        "version": PEN_VERSION,
        "variables": build_variables(tg),
        "children": [compile_reusable(c, tg) for c in idx.all()],
    }


def _descendants_for(node: GraphNode, c: Contract) -> Dict[str, Dict[str, Any]]:
    """根据契约 allowedDescendantOverrides 把 props 映射成 descendants override。"""
    overrides = c.pencil.get("allowedDescendantOverrides", {})
    desc: Dict[str, Dict[str, Any]] = {}
    # 反向：allowedDescendantOverrides 形如 {"label.content": "props.label"}
    for path, source in overrides.items():
        if not source.startswith("props."):
            continue
        prop_name = source[len("props."):]
        if prop_name in node.props:
            head, _, rest = path.partition(".")
            desc.setdefault(head, {})[rest or "content"] = node.props[prop_name]
    return desc


def _instance_node(node: GraphNode, idx: ContractIndex) -> Dict[str, Any]:
    c = idx.get(node.component)
    ref_id = node.component  # 指向 library 中 id=contract.id 的 reusable 组件
    inst: Dict[str, Any] = {
        "id": node.id,
        "type": "ref",
        "ref": ref_id,
        "metadata": {
            "componentId": node.component,
            "system": c.system if c else None,
            "contractVersion": c.version if c else None,
            "variant": node.variant or {},
            "dataBinding": node.data_binding,
        },
    }
    if c:
        desc = _descendants_for(node, c)
        if desc:
            inst["descendants"] = desc
        # token 化 fill（root.fill）从 token_refs 或 tokenBindings
        if "root.fill" in c.token_bindings and "root.fill" in node.token_refs:
            inst["fill"] = "$" + _var_name(node.token_refs["root.fill"])
    # slots → 实例的 slot 子节点（ref 实例可替换 children）
    slot_children: Dict[str, List[Dict[str, Any]]] = {}
    for sname, kids in node.slots.items():
        slot_children[sname] = [_instance_node(k, idx) for k in kids]
    if slot_children:
        inst["slots"] = slot_children
    # 直接子节点
    if node.children:
        inst["children"] = [_instance_node(k, idx) for k in node.children]
    return inst


def compile_page(graph: SemanticGraph, idx: ContractIndex, tg: Optional[TokenGraph] = None) -> Dict[str, Any]:
    """把语义图编译为 Pencil 页面 .pen。"""
    mode = graph.project.get("themeMode")
    pen: Dict[str, Any] = {
        "version": PEN_VERSION,
        "variables": build_variables(tg, mode),
        "children": [],
    }
    for page in graph.pages:
        page_frame: Dict[str, Any] = {
            "id": page["id"], "type": "frame", "name": page.get("title", page["id"]),
            "layout": "vertical", "width": page.get("width", 1440),
            "metadata": {"type": "page", "system": graph.project.get("system")},
        }
        page_frame["children"] = [_instance_node(root, idx) for root in graph.roots_by_page.get(page["id"], [])]
        pen["children"].append(page_frame)
    return pen
