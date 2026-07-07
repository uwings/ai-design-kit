"""KC（知识编译引擎）导出接口——架构预留接入点。

v1：仅返回/写入导出清单（contracts + cards + 意图索引路径），不接入 KC、不建向量。
未来 KC 消费此清单 + 编译产物建向量副本，专门负责设计规范的语义检索与召回。
届时 retriever.py 切换 kc 后端即可。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from ..kit import Kit, PROJECT_ROOT


def export_for_kc(system: str, write: bool = True) -> Dict[str, Any]:
    """导出某体系的 KC 消费清单。"""
    kit = Kit.load()
    if not kit.has_system(system):
        raise FileNotFoundError(f"system not found: {system}")
    idx = kit.load_contracts(system)
    manifest: Dict[str, Any] = {
        "system": system,
        "kcHookup": {"enabled": False, "note": "v1 仅导出清单；KC 接入后由 KC 建向量副本并 enable=true"},
        "contractFiles": [f"systems/{system}/components/{c.id.split('.', 1)[-1]}.contract.json"
                          for c in idx.all()],
        "contractIds": idx.registered_ids(),
        "tokenGraph": f"systems/{system}/tokens/token-graph.json",
        "compositionsDir": f"systems/{system}/compositions/",
        "indexArtifacts": {
            "componentCards": "index/component-cards.json",
            "patternCards": "index/pattern-cards.json",
            "intentIndex": "index/intent-index.json",
            "scenarioCards": "index/scenario-cards.json",
        },
        "intentsCovered": sorted({i for c in idx.all() for i in c.intents}),
    }
    if write:
        out = PROJECT_ROOT / "index" / "_kc" / f"{system}.manifest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
