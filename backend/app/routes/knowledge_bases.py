import os

from fastapi import APIRouter
from sqlalchemy import select

from ..data.db import get_session
from ..utils.response import fail, ok
from ..data.models import KnowledgeBase
from ..data.schemas import KnowledgeBaseCreateIn, KnowledgeBaseOut

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
