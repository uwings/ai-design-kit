"""语义操作应用：把 ops 序列作用到组件图上，构建唯一真相源。

结构错误（父节点不存在、节点 id 重复）在此抛出；契约级问题（组件未注册、variant 非法、
slot 越界、token 违规）留给 validator 拦截，保证 build 不被单条违规中断。
"""
from __future__ import annotations

from typing import List, Optional

from . import schemas
from .graph import GraphNode, SemanticGraph, empty_graph


class OpError(Exception):
    pass


def _make_node(spec: dict, component_id: str) -> GraphNode:
    if "id" not in spec:
        raise OpError(f"node spec missing id: {spec}")
    return GraphNode(
        id=spec["id"],
        component=component_id,
        variant=spec.get("variant", {}) or {},
        props=spec.get("props", {}) or {},
    )


def apply_op(op: dict, graph: SemanticGraph) -> SemanticGraph:
    kind = op.get("op")
    if kind == "component.insert":
        node = _make_node(op["node"], op["componentId"])
        if node.id in graph.nodes_by_id:
            raise OpError(f"duplicate node id on insert: {node.id}")
        parent_id = op.get("parentId")
        if parent_id is None or parent_id == "" or parent_id == "null":
            page = graph.pages[0]
            graph.roots_by_page[page["id"]].append(node)
            graph.nodes_by_id[node.id] = node
        else:
            parent = graph.get(parent_id)
            if parent is None:
                raise OpError(f"insert: parent not found: {parent_id}")
            slot = op.get("parentSlot")
            after = op.get("afterNodeId")
            if slot:
                parent.slots.setdefault(slot, []).append(node)
            elif after:
                sib = parent.children
                idx = next((i for i, c in enumerate(sib) if c.id == after), -1)
                if idx < 0:
                    raise OpError(f"insert: afterNodeId not found: {after}")
                sib.insert(idx + 1, node)
            else:
                parent.children.append(node)
            node.parent = parent
            graph.nodes_by_id[node.id] = node
        return graph

    if kind == "component.setProp":
        node = graph.get(op["nodeId"])
        if node is None:
            raise OpError(f"setProp: node not found: {op['nodeId']}")
        node.props[op["prop"]] = op.get("value")
        return graph

    if kind == "component.setVariant":
        node = graph.get(op["nodeId"])
        if node is None:
            raise OpError(f"setVariant: node not found: {op['nodeId']}")
        node.variant.update(op["variant"] or {})
        return graph

    if kind == "component.fillSlot":
        node = graph.get(op["nodeId"])
        if node is None:
            raise OpError(f"fillSlot: node not found: {op['nodeId']}")
        kids = []
        for spec in op["children"]:
            # 子节点 component 可来自 spec.component 或 contractRefs；优先 spec
            cid = spec.get("component") or (op.get("contractRefs") or [None])[0]
            if not cid:
                raise OpError(f"fillSlot: child missing component id: {spec}")
            child = _make_node(spec, cid)
            child.parent = node
            graph.nodes_by_id[child.id] = child
            kids.append(child)
        node.slots[op["slot"]] = kids
        return graph

    if kind == "component.reorder":
        node = graph.get(op["nodeId"])
        if node is None:
            raise OpError(f"reorder: node not found: {op['nodeId']}")
        slot = op.get("slot")
        order: List[str] = op["order"]
        target = node.slots.get(slot, []) if slot else node.children
        by_id = {c.id: c for c in target}
        new_list = [by_id[i] for i in order if i in by_id]
        # 保留未在 order 中出现的（安全）
        for c in target:
            if c.id not in order:
                new_list.append(c)
        if slot:
            node.slots[slot] = new_list
        else:
            node.children = new_list
        return graph

    if kind == "component.bindData":
        node = graph.get(op["nodeId"])
        if node is None:
            raise OpError(f"bindData: node not found: {op['nodeId']}")
        node.data_binding = op["binding"]
        return graph

    if kind == "token.reference":
        node = graph.get(op["nodeId"])
        if node is None:
            raise OpError(f"token.reference: node not found: {op['nodeId']}")
        node.token_refs[op["path"]] = op["token"]
        return graph

    if kind == "theme.switch":
        graph.project["themeMode"] = op["mode"]
        return graph

    if kind == "layout.applyPattern":
        node = graph.get(op["targetNodeId"])
        if node is None:
            raise OpError(f"applyPattern: target not found: {op['targetNodeId']}")
        node.pattern = op["patternId"]
        return graph

    raise OpError(f"unknown op: {kind}")


def apply_ops(ops: List[dict], system: str = "ant-design", graph: Optional[SemanticGraph] = None,
              validate_schema: bool = True) -> SemanticGraph:
    """把 ops 序列应用到（默认空的）图上，返回构建好的语义图。"""
    if validate_schema:
        schemas.validate_or_raise(ops, "semantic-ops")
    if graph is None:
        graph = empty_graph(system)
    for op in ops:
        apply_op(op, graph)
    return graph
