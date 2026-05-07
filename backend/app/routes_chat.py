from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .db import get_session
from .llm import embed_texts, embedding_enabled, generate_answer
from .models import KnowledgeBase
from .schemas import ChatIn, ChatOut
from .vector_store import search, vector_store_enabled


router = APIRouter()


@router.post("/api/chat", response_model=ChatOut)
async def chat_api(payload: ChatIn):
  kb_id = payload.knowledge_base_id.strip()
  question = payload.question.strip()
  if not kb_id:
    raise HTTPException(status_code=400, detail="knowledge_base_id required")
  if not question:
    raise HTTPException(status_code=400, detail="question required")

  if not embedding_enabled():
    raise HTTPException(status_code=400, detail="DEEPSEEK_API_KEY required")
  if not vector_store_enabled():
    raise HTTPException(status_code=400, detail="QDRANT_URL required")

  kb_name = ""
  with get_session() as session:
    kb = session.get(KnowledgeBase, kb_id)
    if not kb:
      raise HTTPException(status_code=404, detail="knowledge base not found")
    kb_name = kb.name

  qvecs = await embed_texts(texts=[question])
  if not qvecs:
    raise HTTPException(status_code=502, detail="embedding failed")

  hits = search(knowledge_base_id=kb_id, query_vector=qvecs[0], limit=payload.top_k) or []
  retrieved = [
    {
      "file_name": str(h.payload.get("file_name") or ""),
      "page_number": int(h.payload.get("page_number") or 0),
      "text": str(h.payload.get("text") or ""),
      "score": float(h.score),
    }
    for h in hits
    if (h.payload.get("file_name") and h.payload.get("text"))
  ]

  if not retrieved:
    return ChatOut(
      answer=f"当前知识库「{kb_name}」未检索到相关片段，建议换个问法或确认 PDF 是否已成功入库。",
      citations=[],
    )

  context = "\n\n".join(
    [
      f"[{i+1}] 文件：{c['file_name']}；页码：{c['page_number']}\n{c['text']}"
      for i, c in enumerate(retrieved)
    ]
  )
  llm = await generate_answer(question=question, context=context)
  if not llm:
    raise HTTPException(status_code=502, detail="llm generate failed")
  answer = llm

  citations = [
    {"file_name": c["file_name"], "page_number": c["page_number"], "text": c["text"][:500]}
    for c in retrieved
  ]
  return ChatOut(answer=answer, citations=citations)
