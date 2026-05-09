import logging
from dataclasses import dataclass
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ..utils.env import env

logger = logging.getLogger(__name__)

_qdrant_client: Optional[QdrantClient] = None


def vector_store_enabled() -> bool:
    return bool(env("QDRANT_URL"))


def _collection() -> str:
    return env("QDRANT_COLLECTION") or "rag_chunks"


def _get_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client
    url = env("QDRANT_URL")
    api_key = env("QDRANT_API_KEY") or None
    client = QdrantClient(url=url, api_key=api_key)
    _qdrant_client = client
    return client


def ensure_collection(*, vector_size: int) -> None:
    client = _get_client()
    name = _collection()
    collections = client.get_collections().collections
    if any(c.name == name for c in collections):
        info = client.get_collection(name)
        cfg = info.config.params.vectors
        cfg_size = getattr(cfg, "size", None)
        if isinstance(cfg_size, (int, float, str)) and int(cfg_size) != int(vector_size):
            raise ValueError("Qdrant collection vector size mismatch")
        return

    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=int(vector_size), distance=Distance.COSINE),
    )


@dataclass(frozen=True)
class VectorHit:
    id: int
    score: float
    payload: dict[str, Any]


def upsert_points(*, points: list[PointStruct]) -> None:
    client = _get_client()
    client.upsert(collection_name=_collection(), points=points)


def build_point(
    *,
    chunk_id: int,
    vector: list[float],
    knowledge_base_id: str,
    file_id: str,
    file_name: str,
    page_number: int,
    chunk_index: int,
    text: str,
) -> PointStruct:
    payload: dict[str, Any] = {
        "knowledge_base_id": knowledge_base_id,
        "file_id": file_id,
        "file_name": file_name,
        "page_number": int(page_number),
        "chunk_index": int(chunk_index),
        "text": text,
    }
    return PointStruct(id=int(chunk_id), vector=vector, payload=payload)


def delete_by_kb(*, knowledge_base_id: str) -> None:
    if not vector_store_enabled():
        return
    client = _get_client()
    flt = Filter(
        must=[
            FieldCondition(
                key="knowledge_base_id",
                match=MatchValue(value=str(knowledge_base_id)),
            )
        ]
    )
    client.delete(collection_name=_collection(), points_selector=flt)


def search(
    *,
    knowledge_base_id: str,
    query_vector: list[float],
    limit: int,
) -> Optional[list[VectorHit]]:
    if not vector_store_enabled():
        return None

    try:
        client = _get_client()
        flt = Filter(
            must=[
                FieldCondition(
                    key="knowledge_base_id",
                    match=MatchValue(value=str(knowledge_base_id)),
                )
            ]
        )
        res = client.search(
            collection_name=_collection(),
            query_vector=query_vector,
            query_filter=flt,
            limit=int(limit),
            with_payload=True,
        )
        out: list[VectorHit] = []
        for p in res:
            out.append(VectorHit(id=int(p.id), score=float(p.score), payload=dict(p.payload or {})))
        return out
    except (ConnectionError, OSError, ValueError) as e:
        logger.warning("Qdrant search failed: %s", e)
        return None
