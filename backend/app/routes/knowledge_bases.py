import os

from fastapi import APIRouter
from sqlalchemy import select

from ..db import get_session
from ..response import fail, ok
from ..models import Chunk, FileRecord, KnowledgeBase
from ..schemas import KnowledgeBaseCreateIn, KnowledgeBaseOut
from ..services.ingest import batch_embed_and_upsert
from ..services.llm import embedding_enabled
from ..services.vector_store import vector_store_enabled

router = APIRouter()


@router.get("/api/knowledge-bases")
def list_knowledge_bases():
    with get_session() as session:
        rows = (
            session.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
            .scalars()
            .all()
        )
        return ok([KnowledgeBaseOut(id=x.id, name=x.name) for x in rows])


@router.post("/api/knowledge-bases")
def create_knowledge_base(payload: KnowledgeBaseCreateIn):
    name = payload.name.strip()
    if not name:
        return fail("name required")

    kb_id = os.urandom(16).hex()
    kb = KnowledgeBase(id=kb_id, name=name)
    with get_session() as session:
        session.add(kb)
    return ok(KnowledgeBaseOut(id=kb_id, name=name))


@router.post("/api/knowledge-bases/{knowledge_base_id}/reindex")
async def reindex_knowledge_base(knowledge_base_id: str):
    kb_id = knowledge_base_id.strip()
    if not kb_id:
        return fail("knowledge_base_id required")
    if not embedding_enabled():
        return fail("DEEPSEEK_API_KEY required")
    if not vector_store_enabled():
        return fail("QDRANT_URL required")

    with get_session() as session:
        kb = session.get(KnowledgeBase, kb_id)
        if not kb:
            return fail("knowledge base not found")

        rows = (
            session.execute(
                select(
                    Chunk.id,
                    Chunk.text,
                    Chunk.page_number,
                    Chunk.chunk_index,
                    FileRecord.id,
                    FileRecord.file_name,
                )
                .join(FileRecord, FileRecord.id == Chunk.file_id)
                .where(Chunk.knowledge_base_id == kb_id)
                .order_by(Chunk.id.asc())
            ).all()
        )

        if not rows:
            return ok({"ok": True, "embedded": 0})

        items = [
            {
                "chunk_id": int(row[0]),
                "text": str(row[1]),
                "knowledge_base_id": kb_id,
                "file_id": str(row[4]),
                "file_name": str(row[5]),
                "page_number": int(row[2]),
                "chunk_index": int(row[3]),
            }
            for row in rows
        ]
        embedded = await batch_embed_and_upsert(items)

    return ok({"ok": True, "embedded": embedded})
