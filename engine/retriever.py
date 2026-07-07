"""检索器：4 级上下文 + 后端抽象。

v1 默认后端 = fileread（文件直读 + 意图路由，确定性、可解释）。
vector / kc 后端为预留：向量召回/语义检索由知识编译引擎（KC）接入时实现。
"""
from __future__ import annotations

from typing import Optional, Protocol

from . import assemble, indexer
from .kit import Kit


class Retriever(Protocol):
    """检索器接口。retrieve(intent) 返回最小知识包。"""

    def retrieve(self, intent: str, query: str = "", system: Optional[str] = None,
                 include_contracts: Optional[list] = None) -> dict: ...


class FileReadRetriever:
    """v1 默认：文件直读 + 意图路由（index/intent-index.json）。"""

    name = "fileread"

    def retrieve(self, intent: str, query: str = "", system: Optional[str] = None,
                 include_contracts: Optional[list] = None) -> dict:
        return assemble.assemble_knowledge_pack(intent, system, query, include_contracts)


class VectorRetriever:
    """预留：向量语义召回。需 KC 或本地 embedding 后端。v1 不实现。"""

    name = "vector"

    def __init__(self):
        raise NotImplementedError(
            "vector retriever not implemented in v1 — 由知识编译引擎（KC）接入时实现向量召回"
        )


class KCRetriever:
    """预留：经 KC 统一索引召回（含设计偏好/历史决策/品牌调性）。v1 不实现。"""

    name = "kc"

    def __init__(self):
        raise NotImplementedError(
            "kc retriever not implemented in v1 — KC 接入后切换至此后端"
        )


def get_retriever(backend: Optional[str] = None) -> Retriever:
    cfg = indexer._load_json(indexer.INDEX_DIR / "retrieval-config.json",
                             {"defaultBackend": "fileread"})
    backend = backend or cfg.get("defaultBackend", "fileread")
    if backend == "fileread":
        return FileReadRetriever()
    if backend == "vector":
        return VectorRetriever()
    if backend == "kc":
        return KCRetriever()
    raise ValueError(f"unknown retriever backend: {backend}")


def retrieve(intent: str, query: str = "", system: Optional[str] = None,
             include_contracts: Optional[list] = None) -> dict:
    """CLI 入口：按默认后端检索组装最小知识包。"""
    return get_retriever().retrieve(intent, query, system, include_contracts)
