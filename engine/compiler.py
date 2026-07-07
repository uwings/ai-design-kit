"""Contract Compiler —— Source→Contract 自动编译链路的确定性骨干。

系统本质是**编译器**，不是存储仓库。组件契约不是手写的，而是由 AI 从源数据
（公开规范官网/Figma/代码/Storybook）经过 Source Ingestion → Contract Author
编译产出。本模块是这条链路的确定性脊柱：

  源（URL/Figma/代码/Storybook）
    --[agent: 抓取+抽取事实]--> raw 事实
    --[engine: ingest.normalize]----> systems/<sys>/sources/*.snapshot.json   (facts only)
    --[engine: build_compiler_context]--> 编译器上下文（schema/ontology/规则/已注册 id/...）
    --[agent: AI 据上下文从事实编译契约]--> 契约草稿
    --[engine: write_contract]--> schema 校验 + 落盘 systems/<sys>/components/
    --[engine.cli index]--> 检索索引重建

设计参考 PDF p116-117（Source Ingestion：只采事实严禁脑补）+ p121（Contract Author：
从 snapshot 编译契约，hardRules 必须可机器校验）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import schemas
from .kit import Kit, PROJECT_ROOT


def load_snapshot(path) -> dict:
    """加载一个源数据快照（sources/*.snapshot.json）。"""
    p = Path(path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return json.loads(p.read_text(encoding="utf-8"))


def extract_component_facts(snapshot: dict) -> List[dict]:
    """从快照抽取每个组件的事实包（不做语义推断）。"""
    out = []
    for c in snapshot.get("components", []):
        out.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "codeImport": c.get("codeImport") or c.get("code_import"),
            "props": c.get("props", []),
            "variants": c.get("variants", []),
            "variables": c.get("variables", []),
            "figmaKey": c.get("figmaKey"),
            "evidence": c.get("evidence", []),
        })
    return out


def _allowed_intent_tags() -> List[str]:
    tax_path = PROJECT_ROOT / "shared" / "ontology" / "intent-taxonomy.json"
    if not tax_path.exists():
        return []
    return sorted(json.loads(tax_path.read_text(encoding="utf-8")).get("concepts", {}).keys())


def _validator_fn_names() -> List[str]:
    from .validator import RULE_FNS
    return sorted(RULE_FNS.keys())


def _global_rule_summary() -> dict:
    g = PROJECT_ROOT / "shared" / "rules" / "global-hard-rules.json"
    a = PROJECT_ROOT / "shared" / "rules" / "anti-patterns.json"
    out = {"hardRuleIds": [], "antiPatterns": []}
    if g.exists():
        out["hardRuleIds"] = [r.get("id") for r in json.loads(g.read_text(encoding="utf-8")).get("rules", [])]
    if a.exists():
        out["antiPatterns"] = [ap.get("name") for ap in json.loads(a.read_text(encoding="utf-8")).get("antiPatterns", [])]
    return out


def _decision_tree() -> dict:
    p = PROJECT_ROOT / "shared" / "ontology" / "component-decision-tree.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def build_compiler_context(system: str, snapshot_path, *, for_tokens: bool = False) -> dict:
    """构建 AI 编译契约所需的完整上下文（确定性）。AI 据此 + 事实编译出合法契约。"""
    kit = Kit.load()
    snapshot = load_snapshot(snapshot_path)
    facts = extract_component_facts(snapshot)
    component_ids = [f["id"] for f in facts if f.get("id")]

    # 已存在的体系资源（扩展时作为 sibling；新体系则空）
    token_ids: List[str] = []
    registered_ids: List[str] = []
    if kit.has_system(system):
        tg = kit.load_tokens(system)
        if tg:
            token_ids = sorted(tg.tokens.keys())
        registered_ids = kit.load_contracts(system).registered_ids()

    # 映射约定
    react_map = kit.system_dir(system) / "mappings" / "kit-to-react.json"
    pencil_map = kit.system_dir(system) / "mappings" / "kit-to-pencil.json"

    ctx = {
        "compileMode": "tokens+contracts" if for_tokens else "contracts",
        "system": system,
        "source": {
            "kind": snapshot.get("sourceKind"),
            "url": snapshot.get("sourceUrl"),
            "notes": snapshot.get("notes"),
            "ingestedAt": snapshot.get("ingestedAt"),
        },
        "contractSchema": {
            "name": "component-contract",
            "required": ["id", "version", "system", "displayName", "semanticRole", "meaning",
                         "variants", "props", "hardRules", "pencil", "code"],
            "file": "schemas/component-contract.schema.json",
            "notes": "additionalProperties=false；每条 hardRule 必须 kind∈[schema,graph,token,slot,fn] 且可机器校验",
        },
        "systemDefaults": {"version": "1.0.0", "newSystem": not kit.has_system(system)},
        "allowedIntentTags": _allowed_intent_tags(),
        "validatorFnNames": _validator_fn_names(),
        "globalRules": _global_rule_summary(),
        "componentDecisionTree": _decision_tree(),
        "registeredSiblingIds": registered_ids,
        "componentIdsInSnapshot": component_ids,
        "availableTokenIds": token_ids,
        "mappings": {
            "react": json.loads(react_map.read_text(encoding="utf-8")) if react_map.exists() else None,
            "pencil": json.loads(pencil_map.read_text(encoding="utf-8")) if pencil_map.exists() else None,
        },
        "componentFacts": facts,
        "tokenRefs": snapshot.get("tokenRefs", []),
        "output": {
            "contractsDir": f"systems/{system}/components",
            "tokensDir": f"systems/{system}/tokens",
            "systemManifest": f"systems/{system}/system.json",
            "generatedMarker": "contracts below are compiled output, not hand-written; regenerate via the ingest→compile pipeline",
        },
        "rules": [
            "严禁脑补：契约字段必须有事实依据（sourceRefs/sourceEvidence 指向 snapshot 证据）。",
            "id 取自 snapshot 的 component id；system 用上下文的 system。",
            "semanticRole + intents 据组件作用选（intents 必须 ⊆ allowedIntentTags）。",
            "tokenBindings 的值若引用 token，必须 ∈ availableTokenIds；新体系可先留 tokenBindings 为空对象，token 编译为并行阶段。",
            "slots.accepts 必须 ⊆ registeredSiblingIds ∪ componentIdsInSnapshot；空数组=接受任意布局内容。",
            "hardRules：可机器校验。图级规则用 kind:'fn' + expr:'fn:<name>'，<name> 必须 ∈ validatorFnNames；其余用 schema/graph/token/slot + 具体 expr。",
            "code.propMap 必须与 mappings.react 的 propMap 一致（若存在）；code.import 取自 snapshot 的 codeImport。",
            "pencil.componentRefPattern = '<component id>'。",
            "低置信判断 → needsReview:true，且不得成为 hardRule。",
        ],
    }
    return ctx


def write_contract(system: str, contract: dict, *, overwrite: bool = True) -> Path:
    """校验契约 schema 并落盘到 systems/<sys>/components/<short>.contract.json。返回写入路径。"""
    schemas.validate_or_raise(contract, "component-contract")
    if contract.get("system") != system:
        raise ValueError(f"contract.system={contract.get('system')!r} != expected {system!r}")
    short = contract["id"].split(".", 1)[-1]
    out_dir = PROJECT_ROOT / "systems" / system / "components"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{short}.contract.json"
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.relative_to(PROJECT_ROOT)


def write_token_graph(system: str, token_graph: dict, *, overwrite: bool = True) -> Path:
    """校验 token-graph schema 并落盘。"""
    schemas.validate_or_raise(token_graph, "token-graph")
    if token_graph.get("system") != system:
        raise ValueError(f"token-graph.system != {system!r}")
    out_dir = PROJECT_ROOT / "systems" / system / "tokens"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "token-graph.json"
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.write_text(json.dumps(token_graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.relative_to(PROJECT_ROOT)


def write_system_manifest(system: str, manifest: dict) -> Path:
    """写体系元信息 system.json。"""
    schemas.validate_or_raise(manifest, "system")
    out_dir = PROJECT_ROOT / "systems" / system
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "system.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.relative_to(PROJECT_ROOT)


def compile_report(system: str) -> dict:
    """汇总某体系的编译产物。"""
    kit = Kit.load()
    if not kit.has_system(system):
        return {"system": system, "exists": False}
    idx = kit.load_contracts(system)
    tg = kit.load_tokens(system)
    return {
        "system": system,
        "exists": True,
        "components": idx.registered_ids(),
        "tokenCount": len(tg.tokens) if tg else 0,
        "tokenIssues": len([1 for _ in range(0)]) if False else None,
        "generatedNote": "compiled via ingest→compile pipeline; not hand-written storage",
    }
