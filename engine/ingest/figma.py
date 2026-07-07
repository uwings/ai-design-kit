"""Figma MCP 接入适配器。

v1 设计：实际的 Figma MCP 调用（get_code_connect_map / get_variable_defs /
search_design_system / get_context_for_code_connect / get_screenshot）由
adk-source-ingestion skill 驱动 agent 执行（agent 持有 Figma MCP 工具）。
本模块定义归一化管线：agent 把抓取结果传入，本模块归一化为快照。

能力边界（来自圣经调研）：Figma MCP 是"抽取器"，不是"真理层"——
它不会默认理解你的设计系统，除非通过 Code Connect / variables / rules 给它约定。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .normalize import normalize_figma_component, normalize_snapshot


def ingest_figma(system: str, figma_key: str, raw_components: List[Dict[str, Any]],
                 tokens: List[str] = None, source_notes: str = "") -> Dict[str, Any]:
    """agent 已从 Figma MCP 抽取 raw_components；本函数归一化为快照。"""
    components = [normalize_figma_component(c) for c in raw_components]
    return normalize_snapshot(
        system=system, source_kind="figma",
        source_url=f"figma://{figma_key}",
        components=components, tokens=tokens,
        notes=source_notes or "ingested via Figma MCP; facts only",
    )
