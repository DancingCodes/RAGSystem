import os

from fastapi import APIRouter, File, Form, UploadFile

from ..data.db import get_session
from ..utils.response import fail, ok
from ..data.models import FileRecord, KnowledgeBase
from ..data.schemas import UploadedFileOut
from ..services.ingest import process_pdf, uploads_dir
from ..services.vector_store import vector_store_enabled

router = APIRouter()


@router.post("/api/documents")
async def add_document(
    file: UploadFile = File(...),
    knowledge_base_id: str = Form(...),
):
    kb_id = knowledge_base_id.strip()

    if not file.filename:
        return fail("file required")
    name = file.filename
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

    await process_pdf(file_id)

    with get_session() as session:
        rec = session.get(FileRecord, file_id)
        if not rec or rec.status != "succeeded":
            return fail("processing failed")

    return ok(UploadedFileOut(id=file_id, file_name=name))
