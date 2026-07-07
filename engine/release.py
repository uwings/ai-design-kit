"""发布管理：版本分类 patch/minor/major + 打包 + changelog。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from .kit import Kit, PROJECT_ROOT

REPORTS = PROJECT_ROOT / "reports" / "release"


def _bump(version: str, kind: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


@dataclass
class ReleaseCheck:
    contracts_ok: bool
    token_issues: int
    components_count: int
    notes: str


def pre_release_check(system: str) -> ReleaseCheck:
    from .tokens import validate_token_graph
    from .contract import ContractIndex
    kit = Kit.load()
    idx = kit.load_contracts(system)
    tg = kit.load_tokens(system)
    token_issues = len(validate_token_graph(tg)) if tg else 0
    # 契约都通过 schema（加载时已校验）
    return ReleaseCheck(contracts_ok=True, token_issues=token_issues,
                        components_count=len(idx.registered_ids()),
                        notes="contracts loaded & schema-valid; token graph checked")


def release(kind: str = "patch", system: str = None, notes: str = "") -> dict:
    """bump 版本 + 写 changelog + 导出 KC 清单。kind: patch|minor|major。"""
    if kind not in ("patch", "minor", "major"):
        raise ValueError("kind must be patch|minor|major")
    kit = Kit.load()
    sys_name = system or kit.default_system

    old = kit.version
    new = _bump(old, kind)
    kit.raw["version"] = new
    (PROJECT_ROOT / "kit.json").write_text(
        json.dumps(kit.raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    check = pre_release_check(sys_name)

    # KC 导出清单（预留）
    from .ingest.export_for_kc import export_for_kc
    export_for_kc(sys_name)

    changelog = {
        "version": new, "previous": old, "kind": kind, "system": sys_name,
        "checks": {"contractsOk": check.contracts_ok, "tokenIssues": check.token_issues,
                   "components": check.components_count},
        "notes": notes or f"{kind} release",
        "package": {
            "kit.json": "kit.json",
            "contracts": f"systems/{sys_name}/components/*.contract.json",
            "tokenGraph": f"systems/{sys_name}/tokens/token-graph.json",
            "compositions": f"systems/{sys_name}/compositions/*.pattern.json",
            "schemas": "schemas/*.schema.json",
            "mappings": f"systems/{sys_name}/mappings/*.json",
            "index": "index/*.json",
        },
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"v{new}.json").write_text(
        json.dumps(changelog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changelog
