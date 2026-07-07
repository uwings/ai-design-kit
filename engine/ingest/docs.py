"""文档 / 品牌 URL 接入适配器。

两类源（用户明确）：(1) Figma 规范文件（走 figma.py）；(2) 品牌官网/公开规范 URL。
本模块处理 (2)：URL → markdown（经 baoyu-url-to-markdown skill / web reader）→
抽取组件事实 → 归一化。实际抓取由 agent 完成，本模块归一化。
"""
from __future__ import annotations

from typing import Any, Dict, List

from .normalize import normalize_snapshot, normalize_url_doc_component


def ingest_docs(system: str, url: str, raw_components: List[Dict[str, Any]],
                tokens: List[str] = None, markdown_notes: str = "") -> Dict[str, Any]:
    components = [normalize_url_doc_component({**c, "sourceUrl": url}) for c in raw_components]
    return normalize_snapshot(
        system=system, source_kind="url", source_url=url,
        components=components, tokens=tokens,
        notes=markdown_notes or "ingested from brand/spec URL via markdown; facts only",
    )
