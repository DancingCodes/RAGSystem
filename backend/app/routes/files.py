import os

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from ..db import get_session
from ..response import fail, ok
from ..models import FileRecord, KnowledgeBase
from ..schemas import UploadedFileOut
from ..services.ingest import process_pdf, uploads_dir
from ..services.llm import embedding_enabled
from ..services.vector_store import vector_store_enabled

router = APIRouter()


@router.post("/api/documents")
async def add_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    knowledge_base_id: str = Form(...),
    file_name: str = Form(...),
):
    kb_id = knowledge_base_id.strip()
    name = file_name.strip()

    if not file.filename:
        return fail("file required")
    if not embedding_enabled():
        return fail("DEEPSEEK_API_KEY required")
    if not vector_store_enabled():
        return fail("QDRANT_URL required")

    file_id = os.urandom(16).hex()
    out_path = uploads_dir() / f"{file_id}.pdf"

    with get_session() as session:
        kb = session.get(KnowledgeBase, kb_id)
        if not kb:
            return fail("knowledge base not found")

        content = await file.read()
        out_path.write_bytes(content)

        rec = FileRecord(
            id=file_id,
            knowledge_base_id=kb_id,
            file_name=name,
            storage_path=str(out_path),
            status="processing",
        )
        session.add(rec)

    background.add_task(process_pdf, file_id)
    return ok(UploadedFileOut(id=file_id, file_name=name, status="processing"))
