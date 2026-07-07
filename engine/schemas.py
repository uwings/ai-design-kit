"""JSON Schema 加载与校验。系统骨架由 schemas/*.schema.json 定义。"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, List

from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = PROJECT_ROOT / "schemas"


class ContractError(Exception):
    """实例不符合 schema 时抛出。"""

    def __init__(self, schema_name: str, errors: List[Any]):
        self.schema_name = schema_name
        self.errors = errors
        lines = [f"Validation failed against {schema_name}:"]
        for e in errors[:20]:
            loc = ".".join(str(p) for p in e.absolute_path) or "<root>"
            lines.append(f"  - [{loc}] {e.message}")
        super().__init__("\n".join(lines))


@lru_cache(maxsize=None)
def load(name: str) -> dict:
    """按短名加载 schema，如 load('component-contract')。"""
    path = SCHEMA_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(load(name))


def iter_errors(instance: Any, schema_name: str) -> List[Any]:
    """返回排序后的校验错误列表（空=通过）。"""
    errs = list(validator(schema_name).iter_errors(instance))
    errs.sort(key=lambda e: list(e.absolute_path))
    return errs


def is_valid(instance: Any, schema_name: str) -> bool:
    return not iter_errors(instance, schema_name)


def validate_or_raise(instance: Any, schema_name: str) -> Any:
    errs = iter_errors(instance, schema_name)
    if errs:
        raise ContractError(schema_name, errs)
    return instance


def schema_names() -> List[str]:
    return sorted(p.stem.replace(".schema", "") for p in SCHEMA_DIR.glob("*.schema.json"))
