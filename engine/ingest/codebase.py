"""代码 + Code Connect 接入适配器。

从组件源码 / Code Connect 映射抽取事实（prop 类型、import 路径、snippet）。
v1：agent 执行代码扫描/GitHub MCP 访问；本模块归一化。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .normalize import normalize_snapshot


def ingest_codebase(system: str, repo_url: str, raw_components: List[Dict[str, Any]],
                    tokens: List[str] = None) -> Dict[str, Any]:
    components = []
    for c in raw_components:
        components.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "codeImport": c.get("import") or c.get("codeImport"),
            "props": c.get("props", []),
            "codeConnect": c.get("codeConnect"),
            "evidence": c.get("evidence", [repo_url]),
        })
    return normalize_snapshot(system, "code", repo_url, components, tokens,
                              notes="ingested from component source + Code Connect")
