from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path.cwd()
ADK = ROOT / "ai-design-kit"
PROFILE_ID = "ant-design-public-docs"
SLUG = "aigateway-antd-admin-console"
CAPTURED_AT = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


SELECTED_COMPONENTS = [
    "antd.layout",
    "antd.menu",
    "antd.breadcrumb",
    "antd.tabs",
    "antd.flex",
    "antd.space",
    "antd.typography",
    "antd.card",
    "antd.statistic",
    "antd.table",
    "antd.tag",
    "antd.badge",
    "antd.progress",
    "antd.alert",
    "antd.form",
    "antd.input",
    "antd.select",
    "antd.date-picker",
    "antd.switch",
    "antd.button",
    "antd.descriptions",
    "antd.timeline",
    "antd.drawer",
    "antd.modal",
    "antd.divider",
]


TOKEN_REFS = [
    "font.size.base",
    "font.lineHeight.base",
    "space.grid.unit",
    "color.text.default",
    "color.text.secondary",
    "color.text.disabled",
    "color.border.default",
    "color.bg.layout",
    "theme.algorithm.default",
]


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def node(node_id: str, node_type: str = "component", **kwargs: object) -> dict:
    data = {"id": node_id, "type": node_type}
    data.update(kwargs)
    return data


def component_op(parent_id: str | None, component_id: str, node_id: str, reason: str, **kwargs: object) -> dict:
    op = {
        "op": "component.insert",
        "componentId": component_id,
        "node": node(node_id, "component", **kwargs),
        "reason": reason,
        "contractRefs": [component_id],
    }
    if parent_id:
        op["parentId"] = parent_id
    if "variant" in kwargs:
        op["variant"] = kwargs["variant"]
    return op


def main() -> None:
    coverage = load_json(ADK / "coverage" / "ant-design-public-docs.coverage.json")
    token_graph = load_json(ADK / "tokens" / "token-graph.json")
    contracts = {path.stem.replace(".contract", ""): path for path in (ADK / "components").glob("antd.*.contract.json")}
    missing = [cid for cid in SELECTED_COMPONENTS if cid not in contracts]
    if missing:
        raise RuntimeError(f"Missing Ant Design contracts: {missing}")

    intent = {