"""编译器派生产物：从契约 + 模式生成检索面（cards + 意图路由表）。

不建向量索引（向量召回是 KC 接入时的扩展点）。本模块只生成确定性、可解释的：
  index/component-cards.json  — 全体系 L0(index)/L1(card) 摘要
  index/pattern-cards.json    — 组合模式摘要
  index/intent-index.json     — intent → {components, patterns, tokens, preferredVariants} 路由表
  index/scenario-cards.json   — 页面场景摘要
  index/retrieval-config.json — 后端配置（fileread；预留 vector/kc）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .contract import ContractIndex
from .kit import Kit, PROJECT_ROOT

INDEX_DIR = PROJECT_ROOT / "index"


def _load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _component_card(c) -> dict:
    """从一个契约生成 L0+L1 card。"""
    do_not = c.raw.get("meaning", {}).get("doNotUseWhen", [])[:3]
    use_when = c.raw.get("meaning", {}).get("useWhen", [])[:3]
    summary = c.raw.get("meaning", {}).get("definition", c.display_name)
    key_variants = {axis: v.get("values", []) for axis, v in c.variants.items()}
    return {
        "id": c.id,
        "system": c.system,
        "L0": {"index": f"{c.display_name} — {summary[:60]}"},
        "L1": {
            "displayName": c.display_name,
            "semanticRole": c.semantic_role,
            "category": c.raw.get("category"),
            "intents": c.intents,
            "summary": summary,
            "keyVariants": key_variants,
            "useWhen": use_when,
            "doNotUseWhen": do_not,
            "tokenized": list(c.token_bindings.keys()),
        },
    }


def _pattern_card(p: dict, system: str) -> dict:
    return {
        "id": p.get("id"),
        "system": p.get("system", system),
        "displayName": p.get("displayName"),
        "intent": p.get("intent", []),
        "requiredComponents": p.get("requiredComponents", []),
        "summary": p.get("description", "")[:160],
        "order": p.get("order", []),
    }


def build_intent_index(kit: Kit, systems: List[str]) -> dict:
    """合并 shared 意图本体 + 各体系 intent-mapping + 模式 intent → 路由表。"""
    taxonomy = _load_json(PROJECT_ROOT / "shared" / "ontology" / "intent-taxonomy.json", {"concepts": {}})
    idx: Dict[str, dict] = {}
    for concept_id, concept in taxonomy.get("concepts", {}).items():
        idx[concept_id] = {
            "definition": concept.get("definition"),
            "components": list(concept.get("allowedComponents", [])),
            "patterns": list(concept.get("relatedPatterns", [])),
            "preferredVariants": concept.get("preferredVariants", {}),
            "riskLevel": concept.get("riskLevel", "none"),
        }
    for sys_name in systems:
        mapping = _load_json(kit.system_dir(sys_name) / "ontology" / "intent-mapping.json",
                             {"byIntent": {}})
        for intent, comps in mapping.get("byIntent", {}).items():
            slot = idx.setdefault(intent, {"components": [], "patterns": [], "preferredVariants": {}})
            for c in comps:
                if c not in slot["components"]:
                    slot["components"].append(c)
        # 模式 intent
        comp_dir = kit.system_dir(sys_name) / "compositions"
        if comp_dir.exists():
            for pf in sorted(comp_dir.glob("*.pattern.json")):
                p = json.loads(pf.read_text(encoding="utf-8"))
                for intent in p.get("intent", []):
                    slot = idx.setdefault(intent, {"components": [], "patterns": [], "preferredVariants": {}})
                    if p["id"] not in slot["patterns"]:
                        slot["patterns"].append(p["id"])
    return idx


def build_index(kit: Kit, systems: List[str]) -> None:
    """生成 index/ 下全部派生产物。"""
    component_cards: List[dict] = []
    pattern_cards: List[dict] = []
    for sys_name in systems:
        idx = kit.load_contracts(sys_name)
        for c in idx.all():
            component_cards.append(_component_card(c))
        comp_dir = kit.system_dir(sys_name) / "compositions"
        if comp_dir.exists():
            for pf in sorted(comp_dir.glob("*.pattern.json")):
                p = json.loads(pf.read_text(encoding="utf-8"))
                pattern_cards.append(_pattern_card(p, sys_name))

    intent_index = build_intent_index(kit, systems)

    # 场景卡（来自 shared/patterns/page-patterns.json）
    page_patterns = _load_json(PROJECT_ROOT / "shared" / "patterns" / "page-patterns.json", {"patterns": []})
    scenario_cards = [
        {"id": p.get("id"), "displayName": p.get("displayName"), "intent": p.get("intent", []),
         "structure": p.get("structure", []), "requiredComponents": p.get("requiredComponents", [])}
        for p in page_patterns.get("patterns", [])
    ]

    retrieval_config = {
        "defaultBackend": "fileread",
        "availableBackends": ["fileread", "vector", "kc"],
        "note": "v1 = 文件直读 + 意图路由（确定性）。vector/kc 由知识编译引擎（KC）接入时实现：KC 消费 index/_kc/<system>.manifest.json 建向量副本。",
        "contextLevels": {"L0": "index", "L1": "card", "L2": "contract", "L3": "deep"},
    }

    _write_json(INDEX_DIR / "component-cards.json", {"cards": component_cards})
    _write_json(INDEX_DIR / "pattern-cards.json", {"patterns": pattern_cards})
    _write_json(INDEX_DIR / "scenario-cards.json", {"scenarios": scenario_cards})
    _write_json(INDEX_DIR / "intent-index.json", intent_index)
    _write_json(INDEX_DIR / "retrieval-config.json", retrieval_config)


def load_intent_index() -> dict:
    return _load_json(INDEX_DIR / "intent-index.json", {})


def load_component_cards() -> List[dict]:
    return _load_json(INDEX_DIR / "component-cards.json", {"cards": []}).get("cards", [])


def load_pattern_cards() -> List[dict]:
    return _load_json(INDEX_DIR / "pattern-cards.json", {"patterns": []}).get("patterns", [])
