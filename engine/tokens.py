"""Token 图：四层 + 别名解析 + 主题模式 + 循环检测 + 影响传播。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from . import schemas

_ALIAS_RE = re.compile(r"^\{([^{}]+)\}$")


@dataclass
class TokenGraph:
    raw: dict
    modes: List[str] = field(default_factory=lambda: ["light"])
    default_mode: str = "light"

    @classmethod
    def from_file(cls, path: Path) -> "TokenGraph":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        schemas.validate_or_raise(data, "token-graph")
        return cls(data, data.get("modes", ["light"]), data.get("defaultMode", "light"))

    @classmethod
    def from_dict(cls, data: dict, validate: bool = True) -> "TokenGraph":
        if validate:
            schemas.validate_or_raise(data, "token-graph")
        return cls(data, data.get("modes", ["light"]), data.get("defaultMode", "light"))

    @property
    def tokens(self) -> Dict[str, dict]:
        return self.raw.get("tokens", {})

    def has(self, token_id: str) -> bool:
        return token_id in self.tokens

    def _raw_value(self, token_id: str, mode: Optional[str] = None) -> Any:
        """返回某 token 在某模式下的'原始'值（可能是别名引用字符串 {x} 或直接值）。"""
        tok = self.tokens.get(token_id)
        if tok is None:
            return None
        if mode and isinstance(tok.get("modes"), dict):
            mv = tok["modes"].get(mode)
            if mv is not None:
                return mv
        if "alias" in tok:
            a = tok["alias"]
            # alias 字段约定为 token id（无花括号）；兼容已带花括号的写法
            return a if isinstance(a, str) and a.startswith("{") else "{" + str(a) + "}"
        return tok.get("value")

    def resolve(self, token_id: str, mode: Optional[str] = None, _seen: Optional[Set[str]] = None) -> Any:
        """递归解析别名，返回最终值。检测到循环返回 None 并记录。"""
        mode = mode or self.default_mode
        seen = _seen or set()
        if token_id in seen:
            return None  # 循环
        seen = seen | {token_id}
        raw = self._raw_value(token_id, mode)
        if isinstance(raw, str):
            m = _ALIAS_RE.match(raw)
            if m:
                return self.resolve(m.group(1), mode, seen)
        return raw

    def detect_cycles(self) -> List[List[str]]:
        """检测别名循环，返回环路列表。"""
        cycles: List[List[str]] = []

        def follow(tid: str, stack: List[str]) -> Optional[List[str]]:
            tok = self.tokens.get(tid)
            if tok is None:
                return None
            raw = self._raw_value(tid)
            if not isinstance(raw, str):
                return None
            m = _ALIAS_RE.match(raw)
            if not m:
                return None
            target = m.group(1)
            if target in stack:
                idx = stack.index(target)
                return stack[idx:] + [target]
            return follow(target, stack + [target])

        for tid in self.tokens:
            c = follow(tid, [tid])
            if c and c not in cycles:
                cycles.append(c)
        return cycles

    def check_modes(self) -> List[str]:
        """返回声明了 modes 但缺失某些模式的 token id。"""
        missing: List[str] = []
        for tid, tok in self.tokens.items():
            m = tok.get("modes")
            if isinstance(m, dict):
                if any(mode not in m for mode in self.modes):
                    missing.append(tid)
        return missing

    def affected_by(self, semantic_token_id: str) -> Set[str]:
        """改某 semantic token 会影响哪些 token（别名下游传播）。"""
        affected: Set[str] = set()
        # 反向：找所有（直接或间接）引用 semantic_token_id 的 token
        changed = True
        direct: Set[str] = {semantic_token_id}
        while changed:
            changed = False
            for tid, tok in self.tokens.items():
                if tid in affected or tid in direct:
                    continue
                raw = self._raw_value(tid)
                if isinstance(raw, str):
                    m = _ALIAS_RE.match(raw)
                    if m and (m.group(1) in direct or m.group(1) in affected):
                        affected.add(tid)
                        changed = True
        return affected

    def consumers(self, token_id: str) -> List[str]:
        """哪些组件视觉路径消费此 token（来自 bindings）。"""
        return self.raw.get("bindings", {}).get(token_id, [])

    def hardcoded_check(self, value: Any) -> bool:
        """值是否是硬编码颜色（hex/rgb），而非 token 引用。"""
        if not isinstance(value, str):
            return False
        if value.startswith("$") or _ALIAS_RE.match(value):
            return False
        return bool(re.match(r"^(#[0-9a-fA-F]{3,8}|rgb)", value.strip()))


@dataclass
class TokenIssue:
    kind: str  # cycle | missing-mode | hardcoded | unknown-token
    message: str
    detail: Any = None


def validate_token_graph(tg: TokenGraph) -> List[TokenIssue]:
    issues: List[TokenIssue] = []
    for c in tg.detect_cycles():
        issues.append(TokenIssue("cycle", f"alias cycle: {' -> '.join(c)}", c))
    for tid in tg.check_modes():
        issues.append(TokenIssue("missing-mode", f"token '{tid}' missing some modes {tg.modes}", tid))
    return issues
