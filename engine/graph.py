"""语义设计图（组件图）模型——唯一真相源。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from . import schemas


@dataclass
class GraphNode:
    id: str
    component: str
    variant: dict = field(default_factory=dict)
    props: dict = field(default_factory=dict)
    slots: Dict[str, List["GraphNode"]] = field(default_factory=dict)
    children: List["GraphNode"] = field(default_factory=list)
    token_refs: Dict[str, str] = field(default_factory=dict)  # path -> tokenId
    data_binding: Optional[str] = None
    reason: Optional[str] = None
    pattern: Optional[str] = None  # 套用的组合模式 id
    parent: Optional["GraphNode"] = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {"id": self.id, "component": self.component}
        if self.variant:
            d["variant"] = self.variant
        if self.props:
            d["props"] = self.props
        if self.slots:
            d["slots"] = {k: [n.to_dict() for n in v] for k, v in self.slots.items()}
        if self.children:
            d["children"] = [n.to_dict() for n in self.children]
        if self.token_refs:
            d["tokenRefs"] = self.token_refs
        if self.data_binding:
            d["dataBinding"] = self.data_binding
        if self.reason:
            d["reason"] = self.reason
        if self.pattern:
            d["pattern"] = self.pattern
        return d


@dataclass
class SemanticGraph:
    raw: dict
    project: dict
    pages: List[dict] = field(default_factory=list)
    nodes_by_id: Dict[str, GraphNode] = field(default_factory=dict)
    roots_by_page: Dict[str, List[GraphNode]] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> "SemanticGraph":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict, validate: bool = True) -> "SemanticGraph":
        if validate:
            schemas.validate_or_raise(data, "semantic-graph")
        g = cls(raw=data, project=data.get("project", {}), pages=data.get("pages", []))
        g._index()
        return g

    def _index(self) -> None:
        for page in self.pages:
            roots = [self._build(n, None) for n in page.get("children", [])]
            self.roots_by_page[page["id"]] = roots

    def _build(self, raw: dict, parent: Optional[GraphNode]) -> GraphNode:
        node = GraphNode(
            id=raw["id"],
            component=raw["component"],
            variant=raw.get("variant", {}),
            props=raw.get("props", {}),
            data_binding=raw.get("dataBinding"),
            reason=raw.get("reason"),
            pattern=raw.get("pattern"),
            parent=parent,
            raw=raw,
        )
        node.token_refs = raw.get("tokenRefs", {})
        for slot_name, kids in raw.get("slots", {}).items():
            node.slots[slot_name] = [self._build(k, node) for k in kids]
        node.children = [self._build(k, node) for k in raw.get("children", [])]
        if node.id in self.nodes_by_id:
            raise ValueError(f"duplicate node id: {node.id}")
        self.nodes_by_id[node.id] = node
        return node

    def get(self, node_id: str) -> Optional[GraphNode]:
        return self.nodes_by_id.get(node_id)

    def all_nodes(self) -> List[GraphNode]:
        return list(self.nodes_by_id.values())

    def walk(self) -> Iterator[Tuple[GraphNode, Optional[GraphNode], Optional[str]]]:
        """yield (node, parent, slot_name_or_None)。"""
        def rec(node: GraphNode, parent: Optional[GraphNode], slot_name: Optional[str]):
            yield node, parent, slot_name
            for sname, kids in node.slots.items():
                for k in kids:
                    yield from rec(k, node, sname)
            for c in node.children:
                yield from rec(c, node, None)

        for page in self.pages:
            for root in self.roots_by_page.get(page["id"], []):
                yield from rec(root, None, None)

    def to_dict(self) -> dict:
        pages_out = []
        for p in self.pages:
            page_d = {"id": p["id"], "type": p.get("type", "page"),
                      "width": p.get("width") or 1440,
                      "children": [n.to_dict() for n in self.roots_by_page.get(p["id"], [])]}
            if p.get("title"):
                page_d["title"] = p["title"]
            pages_out.append(page_d)
        return {
            "schemaVersion": self.raw.get("schemaVersion", "0.1"),
            "project": self.project,
            "pages": pages_out,
        }


def empty_graph(system: str, page_id: str = "page", title: str = "", theme_mode: Optional[str] = None,
                name: str = "Untitled") -> SemanticGraph:
    """构造空图，供 ops 应用。"""
    data = {
        "schemaVersion": "0.1",
        "project": {"name": name, "system": system, **({"themeMode": theme_mode} if theme_mode else {})},
        "pages": [{"id": page_id, "type": "page", "title": title, "children": []}],
    }
    return SemanticGraph.from_dict(data)
