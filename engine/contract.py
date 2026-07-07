"""组件契约模型 + 体系级索引加载。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from . import schemas


@dataclass
class Contract:
    """单个组件契约的便捷访问视图。raw 为完整 JSON。"""

    raw: dict

    @classmethod
    def from_file(cls, path: Path) -> "Contract":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        schemas.validate_or_raise(data, "component-contract")
        return cls(data)

    @classmethod
    def from_dict(cls, data: dict, validate: bool = True) -> "Contract":
        if validate:
            schemas.validate_or_raise(data, "component-contract")
        return cls(data)

    @property
    def id(self) -> str:
        return self.raw["id"]

    @property
    def system(self) -> str:
        return self.raw["system"]

    @property
    def version(self) -> str:
        return self.raw["version"]

    @property
    def display_name(self) -> str:
        return self.raw["displayName"]

    @property
    def semantic_role(self) -> str:
        return self.raw["semanticRole"]

    @property
    def intents(self) -> List[str]:
        return self.raw.get("intents", [])

    @property
    def variants(self) -> dict:
        return self.raw.get("variants", {})

    @property
    def props(self) -> dict:
        return self.raw.get("props", {})

    @property
    def slots(self) -> dict:
        return self.raw.get("slots", {})

    @property
    def token_bindings(self) -> dict:
        return self.raw.get("tokenBindings", {})

    @property
    def hard_rules(self) -> List[dict]:
        return self.raw.get("hardRules", [])

    @property
    def soft_rules(self) -> List[str]:
        return self.raw.get("softRules", [])

    @property
    def composition_rules(self) -> List[dict]:
        return self.raw.get("compositionRules", [])

    @property
    def pencil(self) -> dict:
        return self.raw.get("pencil", {})

    @property
    def code(self) -> dict:
        return self.raw.get("code", {})

    def variant_values(self, axis: str) -> List[str]:
        return self.variants.get(axis, {}).get("values", [])

    def slot_contract(self, slot_name: str) -> dict:
        return self.slots.get(slot_name, {})


@dataclass
class ContractIndex:
    """体系内所有契约的索引。"""

    by_id: Dict[str, Contract] = field(default_factory=dict)
    system_dir: Optional[Path] = None

    @classmethod
    def load_system(cls, system_dir: Path) -> "ContractIndex":
        system_dir = Path(system_dir)
        idx = cls(system_dir=system_dir)
        comp_dir = system_dir / "components"
        if comp_dir.exists():
            for p in sorted(comp_dir.glob("*.contract.json")):
                c = Contract.from_file(p)
                idx.by_id[c.id] = c
        return idx

    def get(self, component_id: str) -> Optional[Contract]:
        return self.by_id.get(component_id)

    def __contains__(self, component_id: str) -> bool:
        return component_id in self.by_id

    def all(self) -> List[Contract]:
        return list(self.by_id.values())

    def registered_ids(self) -> List[str]:
        return sorted(self.by_id.keys())

    def components_for_intent(self, intent: str) -> List[Contract]:
        return [c for c in self.by_id.values() if intent in c.intents]
