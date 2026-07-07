"""把不同源的原始抽取归一化为 sources/*.snapshot.json。

归一化原则（来自架构圣经）：严禁脑补——只采集有证据的事实；不做语义推断
（语义推断在 contract-author 阶段，带 confidence）。
"""
from __future__ import annotations

from typing import Any, Dict, List

SCHEMA_VERSION = "0.1"


def normalize_snapshot(system: str, source_kind: str, source_url: str,
                       components: List[Dict[str, Any]], tokens: List[str] = None,
                       notes: str = "") -> Dict[str, Any]:
    """把抽取到的事实归一化为标准快照。"""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "system": system,
        "sourceKind": source_kind,
        "sourceUrl": source_url,
        "notes": notes or "normalized snapshot; facts only, no inference",
        "components": components,
        "tokenRefs": tokens or [],
        "coverage": {"componentsSelected": len(components)},
    }


def normalize_figma_component(raw: Dict[str, Any]) -> Dict[str, Any]:
    """归一化一个 Figma MCP 抽取的组件事实。"""
    return {
        "id": raw.get("canonicalId") or raw.get("id"),
        "name": raw.get("name"),
        "figmaKey": raw.get("key"),
        "figmaNodeId": raw.get("node_id") or raw.get("nodeId"),
        "codeImport": raw.get("codeImport"),
        "props": raw.get("props", []),
        "variants": raw.get("variants", []),
        "variables": raw.get("variables", []),
        "evidence": raw.get("evidence", []),
    }


def normalize_url_doc_component(raw: Dict[str, Any]) -> Dict[str, Any]:
    """归一化从品牌官网/公开规范文档（URL→markdown）抽取的组件事实。"""
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "codeImport": raw.get("codeImport"),
        "props": raw.get("props", []),
        "evidence": raw.get("evidence", []),
        "sourceUrl": raw.get("sourceUrl"),
    }
