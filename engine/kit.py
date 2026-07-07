"""Kit 加载器：加载 kit.json + 体系的契约与 token 图。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from . import schemas
from .contract import ContractIndex
from .tokens import TokenGraph

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEMS_DIR = PROJECT_ROOT / "systems"


@dataclass
class Kit:
    raw: dict
    root: Path

    @classmethod
    def load(cls, root: Path = PROJECT_ROOT) -> "Kit":
        data = json.loads((root / "kit.json").read_text(encoding="utf-8"))
        return cls(data, root)

    @property
    def name(self) -> str:
        return self.raw["name"]

    @property
    def version(self) -> str:
        return self.raw["version"]

    def systems(self) -> List[str]:
        return list(self.raw.get("systems", []))

    @property
    def default_system(self) -> str:
        return self.raw.get("defaultSystem") or (self.systems()[0] if self.systems() else "ant-design")

    def system_dir(self, name: str) -> Path:
        return self.root / "systems" / name

    def has_system(self, name: str) -> bool:
        return self.system_dir(name).exists()

    def load_contracts(self, system: str) -> ContractIndex:
        return ContractIndex.load_system(self.system_dir(system))

    def load_tokens(self, system: str) -> Optional[TokenGraph]:
        p = self.system_dir(system) / "tokens" / "token-graph.json"
        if not p.exists():
            return None
        return TokenGraph.from_file(p)

    def token_issues(self, system: str) -> list:
        from .tokens import validate_token_graph
        tg = self.load_tokens(system)
        if tg is None:
            return []
        return [f"{i.kind}: {i.message}" for i in validate_token_graph(tg)]
