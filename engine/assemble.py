"""assemble：按意图组装最小知识包（与 KC 同构思路，但 v1 不用向量）。

设计时 AI 看到的应该是：
  全局规则摘要 → 相关 ontology → 候选组件 card(L1) → 实用组件 full contract(L2)
  → 相关 composition pattern → 必要 token 子图 → 少量 good/bad examples
模型不"记住整个组件库"，而是按需取最小知识包。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from . import indexer
from .kit import Kit, PROJECT_ROOT


def _load(path: Path, default=None):
    if not path or not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _token_subgraph(kit: Kit, system: str, token_ids: List[str]) -> dict:
    tg = kit.load_tokens(system)
    if tg is None:
        return {"tokens": {}}
    sub = {}
    for tid in token_ids:
        if tid in tg.tokens:
            sub[tid] = tg.tokens[tid]
            # 解析出最终值（便于 AI 理解）
            sub[tid]["_resolved"] = {"light": tg.resolve(tid, "light"), "dark": tg.resolve(tid, "dark")}
    return {"system": system, "modes": tg.modes, "tokens": sub}


def assemble_knowledge_pack(intent: str, system: Optional[str] = None, query: str = "",
                            include_contracts: Optional[List[str]] = None) -> dict:
    """组装最小知识包。intent 路由召回候选；include_contracts 显式追加必用组件。"""
    kit = Kit.load()
    system = system or kit.default_system
    intent_index = indexer.load_intent_index()
    cards_all = {c["id"]: c for c in indexer.load_component_cards()}
    patterns_all = {p["id"]: p for p in indexer.load_pattern_cards()}

    entry = intent_index.get(intent, {})
    candidate_ids: List[str] = []
    for cid in entry.get("components", []):
        if cid not in candidate_ids:
            candidate_ids.append(cid)
    if include_contracts:
        for cid in include_contracts:
            if cid not in candidate_ids:
                candidate_ids.append(cid)

    # 相关 ontology
    ontology = {"intent": intent, "definition": entry.get("definition"),
                "preferredVariants": entry.get("preferredVariants", {}),
                "riskLevel": entry.get("riskLevel", "none")}

    # 候选组件 L1 cards
    candidate_cards = [cards_all[cid] for cid in candidate_ids if cid in cards_all]

    # 实用组件 full contract (L2) —— 按候选加载（避免一次性塞整个库）
    contract_idx = kit.load_contracts(system)
    full_contracts = {}
    consumed_tokens: List[str] = []
    for cid in candidate_ids:
        c = contract_idx.get(cid)
        if c:
            full_contracts[cid] = c.raw
            for texpr in c.token_bindings.values():
                # 取 token 表达式里的具名 id（忽略占位符）
                if "{" not in texpr and "}" not in texpr and texpr not in consumed_tokens:
                    consumed_tokens.append(texpr)

    # 相关 composition patterns
    related_patterns = [patterns_all[pid] for pid in entry.get("patterns", []) if pid in patterns_all]
    # 体系内全模式也列摘要（供 plan 阶段参考）
    system_patterns = [p for p in indexer.load_pattern_cards() if p.get("system") == system]

    # good/bad 示例（从候选契约里抽）
    examples = {}
    for cid, c in full_contracts.items():
        ex = c.get("examples", {})
        if ex:
            examples[cid] = ex

    # 全局规则摘要
    global_rules = _load(PROJECT_ROOT / "shared" / "rules" / "global-hard-rules.json", {})
    anti_patterns = _load(PROJECT_ROOT / "shared" / "rules" / "anti-patterns.json", {})
    top_anti = [a["name"] for a in anti_patterns.get("antiPatterns", [])][:5]

    return {
        "intent": intent,
        "system": system,
        "query": query,
        "ontology": ontology,
        "globalRulesSummary": {"hard": [r.get("id") for r in global_rules.get("rules", [])],
                               "topAntiPatterns": top_anti},
        "candidateCards": candidate_cards,           # L1
        "contracts": full_contracts,                  # L2（按需加载的实用组件）
        "relatedPatterns": related_patterns,
        "systemPatterns": system_patterns,
        "tokenSubgraph": _token_subgraph(kit, system, consumed_tokens),
        "examples": examples,
        "note": "最小知识包——按意图路由召回，非全库。向量召回由 KC 接入。",
    }
