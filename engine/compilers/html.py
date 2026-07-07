"""语义图 → 静态 HTML。token → CSS 变量。结构镜像语义图，data-component 带组件身份。

v1 HTML 是语义图的结构镜像（非像素级 AntD 还原）；它证明同一语义源同时编译出 Pencil 与 HTML。
"""
from __future__ import annotations

from typing import List, Optional

from ..contract import ContractIndex
from ..graph import GraphNode, SemanticGraph
from ..tokens import TokenGraph

_TAG_HINT = {
    "button": "button", "input": "input", "select": "select", "form": "form",
    "table": "table", "modal": "section", "menu": "nav", "breadcrumb": "nav",
    "alert": "div", "tag": "span", "badge": "span", "switch": "button",
    "card": "article", "layout": "div", "flex": "div", "space": "div",
    "typography": "div", "divider": "hr", "tabs": "div", "descriptions": "dl",
}


def _tag_for(component_id: str) -> str:
    short = component_id.split(".")[-1]
    return _TAG_HINT.get(short, "div")


def _escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _emit(node: GraphNode, idx: ContractIndex, indent: str) -> str:
    tag = _tag_for(node.component)
    c = idx.get(node.component)
    label_prop = None
    if c:
        for p, cp in c.code.get("propMap", {}).items():
            if cp == "children":
                label_prop = p
                break
    attrs = [f'data-component="{_escape(node.component)}"',
             f'class="adk-{node.component.replace(".", "-")}"']
    for k, v in node.variant.items():
        attrs.append(f'data-variant-{k}="{_escape(v)}"')

    children_html: List[str] = []
    if label_prop and label_prop in node.props:
        children_html.append(f"{indent}  {_escape(node.props[label_prop])}")
    for kids in node.slots.values():
        for k in kids:
            children_html.append(_emit(k, idx, indent + "  "))
    for k in node.children:
        children_html.append(_emit(k, idx, indent + "  "))

    if tag in ("input", "hr") and not children_html:
        return f"{indent}<{tag} {' '.join(attrs)} />"
    if not children_html:
        return f"{indent}<{tag} {' '.join(attrs)}></{tag}>"
    body = "\n".join(children_html)
    return f"{indent}<{tag} {' '.join(attrs)}>\n{body}\n{indent}</{tag}>"


def _css_vars(tg: Optional[TokenGraph], mode: Optional[str]) -> str:
    if not tg:
        return ""
    use_mode = mode or tg.default_mode
    lines = [f"  --{k.replace('.', '-')}: {tg.resolve(k, use_mode)};" for k in sorted(tg.tokens)]
    return "  <style>\n    :root {\n" + "\n".join("      " + l for l in lines) + "\n    }\n  </style>\n" if lines else ""


def compile_html(graph: SemanticGraph, idx: ContractIndex, tg: Optional[TokenGraph] = None) -> str:
    mode = graph.project.get("themeMode")
    title = graph.project.get("name", "ADK Page")
    body_parts: List[str] = []
    for page in graph.pages:
        for root in graph.roots_by_page.get(page["id"], []):
            body_parts.append(_emit(root, idx, "    "))
    body = "\n".join(body_parts)
    css = _css_vars(tg, mode)
    return f"""<!doctype html>
<html lang="zh-CN" data-system="{_escape(graph.project.get('system', ''))}" data-mode="{_escape(mode or 'light')}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(title)}</title>
{css}  <style>
    body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; margin: 0; }}
    .adk-page {{ padding: 24px; }}
  </style>
</head>
<body>
  <main class="adk-page">
{body}
  </main>
</body>
</html>
"""
