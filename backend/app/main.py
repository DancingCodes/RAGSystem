from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .db import Base, engine, get_session
from .llm import generate_answer
from .models import Chunk, FileRecord, KnowledgeBase
from .pdf_ingest import chunk_text, extract_pdf_pages
from .retrieval import retrieve_top_k
from .schemas import ChatIn, ChatOut, KnowledgeBaseCreateIn, KnowledgeBaseOut, UploadedFileOut


Base.metadata.create_all(bind=engine)

app = FastAPI(title="RAGSystem API")

app.add_middleware(
  CORSMiddleware,
  allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
  ],
  allow_origin_regex=r"^http://192\.168\.\d+\.\d+:3000$",
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)


def _uploads_dir() -> Path:
  base_dir = Path(__file__).resolve().parent.parent
  data_dir = base_dir / "data"
  uploads = data_dir / "uploads"
  uploads.mkdir(parents=True, exist_ok=True)
  return uploads


@app.get("/api/health")
def health():
  return {"ok": True}


@app.get("/api/knowledge-bases", response_model=list[KnowledgeBaseOut])
def list_knowledge_bases():
  with get_session() as session:
    rows = session.execute(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())).scalars().all()
    return [KnowledgeBaseOut(id=x.id, name=x.name) for x in rows]


@app.post("/api/knowledge-bases", response_model=KnowledgeBaseOut)
def create_knowledge_base(payload: KnowledgeBaseCreateIn):
  name = payload.name.strip()
  if not name:
    raise HTTPException(status_code=400, detail="name required")

  kb_id = os.urandom(16).hex()
  kb = KnowledgeBase(id=kb_id, name=name)
  with get_session() as session:
    session.add(kb)
  return KnowledgeBaseOut(id=kb_id, name=name)


def _process_pdf(file_id: str):
  with get_session() as session:
    file_row = session.get(FileRecord, file_id)
    if not file_row:
      return
    kb_id = file_row.knowledge_base_id
    path = file_row.storage_path

    try:
      pages = extract_pdf_pages(path)
      chunk_count = 0
      for page_number, text in pages:
        chunks = chunk_text(text)
        for idx, c in enumerate(chunks):
          session.add(
            Chunk(
              knowledge_base_id=kb_id,
              file_id=file_id,
              page_number=page_number,
              chunk_index=idx,
              text=c,
            )
          )
          chunk_count += 1

      if chunk_count == 0:
        file_row.status = "failed"
      else:
        file_row.status = "succeeded"
      session.add(file_row)
    except Exception:
      file_row.status = "failed"
      session.add(file_row)
      raise


@app.post("/api/files", response_model=UploadedFileOut)
async def upload_file(
  background: BackgroundTasks,
  knowledge_base_id: str = Form(...),
  file: UploadFile = File(...),
):
  if not knowledge_base_id.strip():
    raise HTTPException(status_code=400, detail="knowledge_base_id required")
  if file.content_type not in (None, "", "application/pdf"):
    raise HTTPException(status_code=400, detail="only pdf supported")

  file_id = os.urandom(16).hex()
  uploads = _uploads_dir()
  out_path = uploads / f"{file_id}.pdf"

  with get_session() as session:
    kb = session.get(KnowledgeBase, knowledge_base_id)
    if not kb:
      raise HTTPException(status_code=404, detail="knowledge base not found")

    with out_path.open("wb") as f:
      await file.seek(0)
      shutil.copyfileobj(file.file, f)

    rec = FileRecord(
      id=file_id,
      knowledge_base_id=knowledge_base_id,
      file_name=file.filename or "unknown.pdf",
      storage_path=str(out_path),
      status="processing",
    )
    session.add(rec)

  background.add_task(_process_pdf, file_id)
  return UploadedFileOut(id=file_id, file_name=file.filename or "unknown.pdf", status="processing")


@app.post("/api/chat", response_model=ChatOut)
async def chat_api(payload: ChatIn):
  kb_id = payload.knowledge_base_id.strip()
  question = payload.question.strip()
  if not kb_id:
    raise HTTPException(status_code=400, detail="knowledge_base_id required")
  if not question:
    raise HTTPException(status_code=400, detail="question required")

  with get_session() as session:
    kb = session.get(KnowledgeBase, kb_id)
    if not kb:
      raise HTTPException(status_code=404, detail="knowledge base not found")

    rows = session.execute(
      select(Chunk.text, Chunk.page_number, FileRecord.file_name)
      .join(FileRecord, FileRecord.id == Chunk.file_id)
      .where(Chunk.knowledge_base_id == kb_id)
    ).all()

  if not rows:
    return ChatOut(
      answer=f"当前知识库「{kb.name}」暂无可检索内容（可能还在入库中或入库失败）。",
      citations=[],
    )

  texts: list[str] = []
  metas: list[tuple[str, int]] = []
  for text, page_number, file_name in rows:
    texts.append(text)
    metas.append((file_name, page_number))

  retrieved = retrieve_top_k(
    question=question,
    texts=texts,
    metas=metas,
    top_k=payload.top_k,
  )

  if not retrieved:
    return ChatOut(
      answer="未在已入库内容中检索到相关片段，建议换个问法或确认 PDF 是否已成功入库。",
      citations=[],
    )

  context = "\n\n".join(
    [
      f"[{i+1}] 文件：{c.file_name}；页码：{c.page_number}\n{c.text}"
      for i, c in enumerate(retrieved)
    ]
  )
  llm = await generate_answer(question=question, context=context)
  answer = llm or (
    "当前未配置大模型（OPENAI_API_KEY/OPENAI_MODEL）。下面是检索到的相关片段，可先用于验证检索效果：\n\n"
    + context
  )

  citations = [
    {"file_name": c.file_name, "page_number": c.page_number, "text": c.text[:500]}
    for c in retrieved
  ]
  return ChatOut(answer=answer, citations=citations)
