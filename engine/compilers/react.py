"""语义图 → React/TSX。源是语义图，不是 .pen，避免丢语义。

用契约 code 段（import / component / propMap）生成真实组件 import 与 props。
token → CSS 变量（:root，作为注释随文件输出；宿主工程可用 resolved_tokens() 另行生成 tokens.css / ConfigProvider 主题）。

编译约定（契约 code 段未表达、由编译器承担的确定性映射；2026-09 为让产物可直接运行而补齐）：
- 非标量 prop（数组 / 对象）→ JSX 表达式（JS 字面量），不再序列化成字符串；
- 图标：icon / prefix / suffix / extra / closeIcon 等位置上形如 `XxxOutlined | XxxFilled | XxxTwoTone` 的字符串
  → `@ant-design/icons` 的真实图标元素。图标名是语义图里的数据，编译器负责把它解析到图标库，AI 仍不画像素；
- 复合组件：antd.layout 的 header / sider / content / footer slot → Layout.Header / Sider / Content / Footer
  （有 sider 时按 antd 惯例嵌套一层内层 Layout），sider* props 落到 Layout.Sider 上；
  antd.grid 带列属性（span / flex / offset / push / pull / order / responsive）时编译为 Col，否则为 Row；
  antd.card 的 header / cover / actions slot → title / cover / actions prop，content slot → children；
  antd.typography 按 variant 轴编译为 Typography.Title / Text / Paragraph；
- 变体轴 → prop：轴名在 propMap 中按映射，否则仅当契约声明了同名 prop 时按轴名传
  （avatar.content 这类纯语义轴不落代码）；button intent=danger → `danger`（antd 语法糖）；
  契约 prop 类型为 boolean 的 'true' / 'false' 字符串 → 布尔；iconOnly 为纯语义 prop，不落代码。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from ..contract import Contract, ContractIndex
from ..graph import GraphNode, SemanticGraph
from ..tokens import TokenGraph

_ICON_RE = re.compile(r"^[A-Z][A-Za-z0-9]*(Outlined|Filled|TwoTone)$")
_ICON_KEYS = {"icon", "prefix", "suffix", "extra", "closeIcon", "expandIcon", "indicator"}
_ICON_PKG = "@ant-design/icons"
_SAFE_TEXT = re.compile(r'^[^"{}<>\\\r\n]*$')

_LAYOUT_SLOTS: Tuple[Tuple[str, str], ...] = (("header", "Layout.Header"), ("content", "Layout.Content"), ("footer", "Layout.Footer"))
_SIDER_PROPS = {"siderTheme": "theme", "siderCollapsed": "collapsed", "siderCollapsible": "collapsible",
                "siderBreakpoint": "breakpoint", "siderWidth": "width"}
_COL_PROPS = ("span", "flex", "offset", "push", "pull", "order", "responsive")
_CARD_SLOT_PROPS = {"header": "title", "cover": "cover", "actions": "actions"}
_TYPOGRAPHY = {"title": "Typography.Title", "text": "Typography.Text", "paragraph": "Typography.Paragraph"}


@dataclass
class _Ctx:
    imports: List[str] = field(default_factory=list)
    icons: Set[str] = field(default_factory=set)


def _short(component_id: str) -> str:
    return component_id.split(".")[-1]


# ---------- 值 → JS ----------

def _js(v, ctx: _Ctx, key: Optional[str] = None) -> str:
    """Python 值 → JS 字面量（写在 JSX 表达式 {} 内）。图标位置上的图标名 → 图标元素。"""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        if key in _ICON_KEYS and _ICON_RE.match(v):
            ctx.icons.add(v)
            return f"<{v} />"
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_js(x, ctx, key) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{json.dumps(str(k))}: {_js(val, ctx, k)}" for k, val in v.items()) + " }"
    return json.dumps(str(v), ensure_ascii=False)


def _attr(name: str, v, ctx: _Ctx, key: Optional[str] = None) -> Optional[str]:
    """一个 JSX 属性。None 不输出；bool 按 JSX 惯例；字符串安全时用引号，否则走表达式。"""
    if v is None:
        return None
    if isinstance(v, bool):
        return name if v else f"{name}={{false}}"
    if isinstance(v, (int, float)):
        return f"{name}={{{v}}}"
    if isinstance(v, str):
        if (key or name) in _ICON_KEYS and _ICON_RE.match(v):
            ctx.icons.add(v)
            return f"{name}={{<{v} />}}"
        if _SAFE_TEXT.match(v):
            return f'{name}="{v}"'
        return f"{name}={{{json.dumps(v, ensure_ascii=False)}}}"
    return f"{name}={{{_js(v, ctx, key or name)}}}"


def _text(s) -> str:
    s = str(s)
    return s if _SAFE_TEXT.match(s) else "{" + json.dumps(s, ensure_ascii=False) + "}"


def _coerce(c: Optional[Contract], prop: str, v):
    """按契约 prop 类型做最小收敛：boolean 的 'true' / 'false' 字符串 → 布尔。"""
    if c and isinstance(v, str) and c.props.get(prop, {}).get("type") == "boolean" and v.lower() in ("true", "false"):
        return v.lower() == "true"
    return v


def _block(tag: str, attrs: List[Optional[str]], kids: List[str], indent: str) -> str:
    head = f"{indent}<{tag}" + "".join(" " + a for a in attrs if a)
    if not kids:
        return head + " />"
    return head + ">\n" + "\n".join(kids) + f"\n{indent}</{tag}>"


# ---------- props / variants ----------

def _props(node: GraphNode, c: Optional[Contract], ctx: _Ctx, short: str, skip: Set[str] = frozenset()) -> Tuple[List[str], List[str]]:
    """返回 (JSX 属性列表, 文本子节点列表)。propMap 映射到 children 的 prop 成为文本子节点。"""
    pm: Dict[str, str] = c.code.get("propMap", {}) if c else {}
    children_prop = next((k for k, v in pm.items() if v == "children"), None)
    attrs: List[str] = []
    texts: List[str] = []
    used: Set[str] = set()
    for k, v in node.props.items():
        if k in skip:
            continue
        if children_prop and k == children_prop:
            texts.append(_text(v))
            continue
        if k == "iconOnly":
            continue
        mapped = pm.get(k, k)
        if "." in mapped or mapped in used:
            continue
        a = _attr(mapped, _coerce(c, k, v), ctx, key=k)
        if a:
            attrs.append(a)
            used.add(mapped)
    for axis, val in (node.variant or {}).items():
        if axis in skip:
            continue
        if short == "button" and axis == "intent" and val == "danger":
            if "danger" not in used:
                attrs.append("danger")
                used.add("danger")
            continue
        mapped = pm.get(axis) or (axis if (c and axis in c.props) else None)
        if not mapped or "." in mapped or mapped in used:
            continue
        a = _attr(mapped, _coerce(c, axis, val), ctx, key=axis)
        if a:
            attrs.append(a)
            used.add(mapped)
    return attrs, texts


# ---------- 节点 ----------

def _emit(node: GraphNode, idx: ContractIndex, ctx: _Ctx, indent: str) -> str:
    c = idx.get(node.component)
    if c and c.code.get("import"):
        ctx.imports.append(c.code["import"])
    short = _short(node.component)
    if short == "layout":
        return _emit_layout(node, c, idx, ctx, indent)
    if short == "grid":
        return _emit_grid(node, c, idx, ctx, indent)
    if short == "typography":
        return _emit_typography(node, c, idx, ctx, indent)
    return _emit_generic(node, c, idx, ctx, indent, short)


def _slot_kids(node: GraphNode, idx: ContractIndex, ctx: _Ctx, indent: str, skip_slots: Set[str] = frozenset()) -> List[str]:
    kids: List[str] = []
    for sname, ks in node.slots.items():
        if sname in skip_slots:
            continue
        kids.extend(_emit(k, idx, ctx, indent) for k in ks)
    kids.extend(_emit(k, idx, ctx, indent) for k in node.children)
    return kids


def _emit_generic(node: GraphNode, c: Optional[Contract], idx: ContractIndex, ctx: _Ctx, indent: str, short: str) -> str:
    tag = (c.code.get("component") if c else None) or short.title()
    attrs, texts = _props(node, c, ctx, short)
    inner = indent + "  "
    if short == "card":
        for sname, pname in _CARD_SLOT_PROPS.items():
            ks = node.slots.get(sname) or []
            if not ks:
                continue
            rendered = [_emit(k, idx, ctx, "").strip() for k in ks]
            if pname == "actions":
                attrs.append(f"actions={{[{', '.join(rendered)}]}}")
            else:
                attrs.append(f"{pname}={{{rendered[0]}}}")
        kids = [inner + t for t in texts] + _slot_kids(node, idx, ctx, inner, skip_slots=set(_CARD_SLOT_PROPS))
    else:
        kids = [inner + t for t in texts] + _slot_kids(node, idx, ctx, inner)
    return _block(tag, attrs, kids, indent)


def _emit_layout(node: GraphNode, c: Optional[Contract], idx: ContractIndex, ctx: _Ctx, indent: str) -> str:
    attrs, _ = _props(node, c, ctx, "layout", skip=set(_SIDER_PROPS))
    sider = node.slots.get("sider") or []
    i1 = indent + "  "
    i2 = i1 + ("  " if sider else "")
    body: List[str] = []
    if sider:
        sattrs = [_attr(_SIDER_PROPS[k], _coerce(c, k, v), ctx, key=k) for k, v in node.props.items() if k in _SIDER_PROPS]
        body.append(_block("Layout.Sider", sattrs, [_emit(k, idx, ctx, i1 + "  ") for k in sider], i1))
    sections: List[str] = []
    for sname, tag in _LAYOUT_SLOTS:
        ks = node.slots.get(sname) or []
        if ks:
            sections.append(_block(tag, [], [_emit(k, idx, ctx, i2 + "  ") for k in ks], i2))
    sections.extend(_emit(k, idx, ctx, i2) for k in node.children)
    if sider:
        body.append(_block("Layout", [], sections, i1))
    else:
        body.extend(sections)
    return _block("Layout", attrs, body, indent)


def _emit_grid(node: GraphNode, c: Optional[Contract], idx: ContractIndex, ctx: _Ctx, indent: str) -> str:
    inner = indent + "  "
    if any(p in node.props for p in _COL_PROPS):
        attrs: List[Optional[str]] = []
        for k, v in node.props.items():
            if k == "responsive" and isinstance(v, dict):
                attrs.extend(_attr(bp, bv, ctx) for bp, bv in v.items())
            elif k in _COL_PROPS:
                attrs.append(_attr(k, v, ctx))
        return _block("Col", attrs, _slot_kids(node, idx, ctx, inner), indent)
    attrs, _ = _props(node, c, ctx, "grid", skip=set(_COL_PROPS))
    return _block("Row", attrs, _slot_kids(node, idx, ctx, inner), indent)


def _emit_typography(node: GraphNode, c: Optional[Contract], idx: ContractIndex, ctx: _Ctx, indent: str) -> str:
    variant = (node.variant or {}).get("variant") or node.props.get("variant") or "text"
    tag = _TYPOGRAPHY.get(variant, "Typography.Text")
    attrs, texts = _props(node, c, ctx, "typography", skip={"variant", "level"})
    attrs = [a for a in attrs if a != 'type="default"']
    level = node.props.get("level") or (node.variant or {}).get("level")
    if tag == "Typography.Title" and level is not None:
        attrs.append(f"level={{{int(level)}}}")
    inner = indent + "  "
    kids = [inner + t for t in texts] + _slot_kids(node, idx, ctx, inner)
    return _block(tag, attrs, kids, indent)


# ---------- tokens ----------

def resolved_tokens(tg: Optional[TokenGraph], mode: Optional[str] = None) -> Dict[str, object]:
    """token 图在某模式下的解析结果（tokenId → 值），供宿主工程生成 tokens.css / 主题配置。"""
    if not tg:
        return {}
    use_mode = mode or tg.default_mode
    return {k: tg.resolve(k, use_mode) for k in sorted(tg.tokens)}


def _css_vars(tg: Optional[TokenGraph], mode: Optional[str]) -> str:
    lines = [f"  --{k.replace('.', '-')}: {v};" for k, v in resolved_tokens(tg, mode).items()]
    return ":root {\n" + "\n".join(lines) + "\n}\n" if lines else ""


# ---------- 入口 ----------

def compile_react(graph: SemanticGraph, idx: ContractIndex, tg: Optional[TokenGraph] = None) -> str:
    mode = graph.project.get("themeMode")
    ctx = _Ctx()
    roots: List[str] = []
    for page in graph.pages:
        for root in graph.roots_by_page.get(page["id"], []):
            roots.append(_emit(root, idx, ctx, "      "))
    seen: Set[str] = set()
    unique_imports = [i for i in ctx.imports if not (i in seen or seen.add(i))]
    if ctx.icons:
        unique_imports.append(f'import {{ {", ".join(sorted(ctx.icons))} }} from "{_ICON_PKG}";')
    comp_name = "".join(p.title() for p in graph.project.get("name", "Page").replace("-", " ").split()) or "Page"
    body = "\n".join(roots)
    css = _css_vars(tg, mode)
    return f"""// AUTO-GENERATED by AI Design Kit — from semantic graph (single source of truth).
// Do not edit by hand to imitate components; change the semantic graph and recompile.
import React from "react";
{chr(10).join(unique_imports)}

/*
{css}
*/
export default function {comp_name}() {{
  return (
    <div className="adk-page" data-system="{graph.project.get('system', '')}">
{body}
    </div>
  );
}}
"""
