"""反馈学习器：把人类纠错/校验失败固化成系统知识（落盘，非对话记忆）。

每条纠错必须落盘成至少一种持久化产物（契约 patch / 规则 patch / good-bad 示例 / 校验器测试）。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from . import schemas
from .contract import Contract
from .kit import Kit, PROJECT_ROOT

MEMORY = PROJECT_ROOT / "memory" / "corrections.jsonl"


def _load(p: Path, default=None):
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def _save(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(p: Path, record: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _patch_contract(contract_path: Path, correction: dict) -> List[str]:
    """对契约应用 patch（追加 hardRule/softRule/example/slot 规则）。返回变更字段。"""
    data = _load(contract_path, {})
    changed: List[str] = []
    patch = correction.get("patch", {})
    # 追加 hardRule
    if patch.get("hardRule"):
        data.setdefault("hardRules", []).append(patch["hardRule"])
        changed.append("hardRules")
    if patch.get("softRule"):
        data.setdefault("softRules", []).append(patch["softRule"])
        changed.append("softRules")
    if patch.get("exampleGood"):
        data.setdefault("examples", {}).setdefault("good", []).append(patch["exampleGood"])
        changed.append("examples.good")
    if patch.get("exampleBad"):
        data.setdefault("examples", {}).setdefault("bad", []).append(patch["exampleBad"])
        changed.append("examples.bad")
    if patch.get("compositionRule"):
        data.setdefault("compositionRules", []).append(patch["compositionRule"])
        changed.append("compositionRules")
    if patch.get("slotRule"):
        slot_name = patch["slotRule"].get("slot")
        if slot_name:
            data.setdefault("slots", {}).setdefault(slot_name, {}).setdefault("rules", []).append(
                patch["slotRule"].get("assert", ""))
            changed.append(f"slots.{slot_name}.rules")
    # 给某 prop 追加约束（maxLength/enum/min 等），validator 的 prop 校验会强制执行
    if patch.get("propConstraint"):
        pc = patch["propConstraint"]
        prop_name = pc.get("prop")
        if prop_name:
            prop = data.setdefault("props", {}).setdefault(prop_name, {})
            for k in ("maxLength", "minLength", "minimum", "maximum"):
                if k in pc:
                    prop[k] = pc[k]
                    changed.append(f"props.{prop_name}.{k}")
            if "enum" in pc:
                prop["enum"] = pc["enum"]
                changed.append(f"props.{prop_name}.enum")
    # 校验改后仍合规
    schemas.validate_or_raise(data, "component-contract")
    _save(contract_path, data)
    return changed


def _patch_rules(correction: dict) -> List[str]:
    target = correction.get("target", {})
    patch = correction.get("patch", {})
    rule_file = target.get("path") or "shared/rules/global-hard-rules.json"
    p = PROJECT_ROOT / rule_file
    data = _load(p, {"rules": []})
    if patch.get("hardRule"):
        data.setdefault("rules", []).append(patch["hardRule"])
        _save(p, data)
        return [rule_file]
    return []


def _write_example(correction: dict, kind: str) -> List[str]:
    """写 good/bad 示例文件。kind: good|bad"""
    target = correction.get("target", {})
    system = target.get("system", "ant-design")
    comp = target.get("componentId") or "general"
    out_dir = PROJECT_ROOT / "systems" / system / "examples" / kind
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{comp}.{correction['id']}.json"
    out = out_dir / fname
    _save(out, {"correctionId": correction["id"], "kind": kind,
                "component": comp, "payload": correction.get("patch", {}),
                "source": correction.get("source", "human review")})
    return [str(out.relative_to(PROJECT_ROOT))]


def apply_correction(correction: dict, write: bool = True) -> Dict[str, Any]:
    """应用一条纠错（符合 correction.schema.json）。返回变更摘要。"""
    schemas.validate_or_raise(correction, "correction")
    target = correction.get("target", {})
    kind = target.get("kind")
    files_changed: List[str] = []
    affected: List[str] = []

    kit = Kit.load()
    system = target.get("system") or kit.default_system

    if kind == "contract":
        comp_id = target.get("componentId")
        if comp_id:
            # 定位契约文件：systems/<sys>/components/<short>.contract.json
            short = comp_id.split(".", 1)[-1]
            cpath = PROJECT_ROOT / "systems" / system / "components" / f"{short}.contract.json"
            if cpath.exists():
                files_changed += _patch_contract(cpath, correction)
                affected.append(comp_id)
            else:
                files_changed += _patch_contract(cpath, correction)  # 写新文件
                affected.append(comp_id)
    elif kind == "rule":
        files_changed += _patch_rules(correction)
    elif kind in ("example", "antiExample"):
        ek = "good" if kind == "example" else "bad"
        files_changed += _write_example(correction, ek)
    else:
        # validator / pattern / token —— v1 记录为待办
        files_changed.append(f"(stub) {kind} patch: {target.get('path')}")

    # 落盘纠错记录（持久化学习）
    record = dict(correction)
    record["appliedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record["filesChanged"] = files_changed
    if write:
        _append_jsonl(MEMORY, record)

    return {
        "correctionId": correction["id"],
        "type": correction.get("type"),
        "filesChanged": files_changed,
        "affectedComponents": affected,
        "validatorsToRerun": ["validate-contracts", "validate-graph"],
    }


def list_corrections() -> List[dict]:
    if not MEMORY.exists():
        return []
    return [json.loads(line) for line in MEMORY.read_text(encoding="utf-8").splitlines() if line.strip()]
