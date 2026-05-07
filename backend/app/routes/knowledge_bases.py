import os

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from ..db import get_session
from ..models import Chunk, FileRecord, KnowledgeBase
from ..schemas import KnowledgeBaseCreateIn, KnowledgeBaseOut
from ..services.llm import embed_texts, embedding_enabled
from ..services.vector_store import build_point, ensure_collection, upsert_points, vector_store_enabled

router = APIRouter()


@router.get("/api/knowledge-bases", response_model=list[KnowledgeBaseOut])
def list_knowledge_bases():
  with get_session() as session:
    rows = (
      session.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()))
      .scalars()
      .all()
    )
    return [KnowledgeBaseOut(id=x.id, name=x.name) for x in rows]


@router.post("/api/knowledge-bases", response_model=KnowledgeBaseOut)
def create_knowledge_base(payload: KnowledgeBaseCreateIn):
  name = payload.name.strip()
  if not name:
    raise HTTPException(status_code=400, detail="name required")

  kb_id = os.urandom(16).hex()
  kb = KnowledgeBase(id=kb_id, name=name)
  with get_session() as session:
    session.add(kb)
  return KnowledgeBaseOut(id=kb_id, name=name)


@router.post("/api/knowledge-bases/{knowledge_base_id}/reindex")
async def reindex_knowledge_base(knowledge_base_id: str):
  kb_id = knowledge_base_id.strip()
  if not kb_id:
    raise HTTPException(status_code=400, detail="knowledge_base_id required")
  if not embedding_enabled():
    raise HTTPException(status_code=400, detail="DEEPSEEK_API_KEY required")
  if not vector_store_enabled():
    raise HTTPException(status_code=400, detail="QDRANT_URL required")

  with get_session() as session:
    kb = session.get(KnowledgeBase, kb_id)
    if not kb:
      raise HTTPException(status_code=404, detail="knowledge base not found")

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
      return {"ok": True, "embedded": 0}

    batch_size = 64
    embedded = 0
    for start in range(0, len(rows), batch_size):
      batch = rows[start : start + batch_size]
      texts = [str(x[1]) for x in batch]
      vectors = await embed_texts(texts=texts)
      if not vectors or len(vectors) != len(batch):
        raise HTTPException(status_code=502, detail="embedding failed")

      ensure_collection(vector_size=len(vectors[0]))
      points = [
        build_point(
          chunk_id=int(row[0]),
          vector=vec,
          knowledge_base_id=kb_id,
          file_id=str(row[4]),
          file_name=str(row[5]),
          page_number=int(row[2]),
          chunk_index=int(row[3]),
          text=str(row[1]),
        )
        for row, vec in zip(batch, vectors)
      ]
      upsert_points(points=points)
      embedded += len(points)

  return {"ok": True, "embedded": embedded}

