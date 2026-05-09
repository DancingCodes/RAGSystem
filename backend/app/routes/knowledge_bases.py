import os

from fastapi import APIRouter
from sqlalchemy import delete, select

from ..data.db import get_session
from ..utils.response import fail, ok
from ..data.models import Chunk, FileRecord, KnowledgeBase
from ..data.schemas import KnowledgeBaseCreateIn, KnowledgeBaseOut
from ..services.vector_store import delete_by_kb

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


@router.delete("/api/knowledge-bases/{knowledge_base_id}")
def delete_knowledge_base(knowledge_base_id: str):
    kb_id = knowledge_base_id.strip()
    if not kb_id:
        return fail("knowledge_base_id required")

    with get_session() as session:
        kb = session.get(KnowledgeBase, kb_id)
        if not kb:
            return fail("knowledge base not found")

        session.execute(delete(Chunk).where(Chunk.knowledge_base_id == kb_id))
        session.execute(delete(FileRecord).where(FileRecord.knowledge_base_id == kb_id))
        session.delete(kb)

    delete_by_kb(knowledge_base_id=kb_id)
    return ok()
