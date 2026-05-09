from fastapi import APIRouter

from ..data.db import get_session
from ..utils.response import fail, ok
from ..data.models import KnowledgeBase
from ..data.schemas import ChatIn, ChatOut, CitationOut
from ..services.llm import chat_enabled, embed_texts, generate_answer
from ..services.vector_store import search, vector_store_enabled

router = APIRouter()


@router.post("/api/chat")
async def chat_api(payload: ChatIn):
    kb_id = payload.knowledge_base_id.strip()
    question = payload.question.strip()
    if not kb_id:
        return fail("knowledge_base_id required")
    if not question:
        return fail("question required")

    if not chat_enabled():
        return fail("DEEPSEEK_API_KEY required")
    if not vector_store_enabled():
        return fail("QDRANT_URL required")

    kb_name = ""
    with get_session() as session:
        kb = session.get(KnowledgeBase, kb_id)
        if not kb:
            return fail("knowledge base not found")
        kb_name = kb.name

    qvecs = await embed_texts(texts=[question])
    if not qvecs:
        return fail("embedding failed")

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
        return ok(ChatOut(
            answer=f"当前知识库「{kb_name}」未检索到相关片段，建议换个问法或确认 PDF 是否已成功入库。",
            citations=[],
        ))

    context = "\n\n".join(
        [
            f"[{i+1}] 文件：{c['file_name']}；页码：{c['page_number']}\n{c['text']}"
            for i, c in enumerate(retrieved)
        ]
    )
    llm = await generate_answer(question=question, context=context)
    if not llm:
        return fail("llm generate failed")
    answer = llm

    citations = [
        CitationOut(
            file_name=str(c["file_name"]),
            page_number=int(c["page_number"]),
            text=str(c["text"])[:500],
        )
        for c in retrieved
    ]
    return ok(ChatOut(answer=answer, citations=citations))
