from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from .db import get_session
from .ingest import process_pdf, save_upload, uploads_dir
from .llm import embedding_enabled
from .models import FileRecord, KnowledgeBase
from .schemas import UploadedFileOut
from .vector_store import vector_store_enabled


router = APIRouter()


@router.post("/api/files", response_model=UploadedFileOut)
async def upload_file(
  background: BackgroundTasks,
  knowledge_base_id: str = Form(...),
  file: UploadFile = File(...),
):
  if not knowledge_base_id.strip():
    raise HTTPException(status_code=400, detail="knowledge_base_id required")
  if file.content_type not in (None, "", "application/pdf"):
    raise HTTPException(status_code=400, detail="only pdf supported")
  if not embedding_enabled():
    raise HTTPException(status_code=400, detail="DEEPSEEK_API_KEY required")
  if not vector_store_enabled():
    raise HTTPException(status_code=400, detail="QDRANT_URL required")

  file_id = os.urandom(16).hex()
  uploads = uploads_dir()
  out_path = uploads / f"{file_id}.pdf"

  with get_session() as session:
    kb = session.get(KnowledgeBase, knowledge_base_id)
    if not kb:
      raise HTTPException(status_code=404, detail="knowledge base not found")

    await save_upload(file_obj=file, out_path=out_path)

    rec = FileRecord(
      id=file_id,
      knowledge_base_id=knowledge_base_id,
      file_name=file.filename or "unknown.pdf",
      storage_path=str(out_path),
      status="processing",
    )
    session.add(rec)

  background.add_task(process_pdf, file_id)
  return UploadedFileOut(id=file_id, file_name=file.filename or "unknown.pdf", status="processing")
