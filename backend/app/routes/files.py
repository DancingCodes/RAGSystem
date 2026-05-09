import os

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..db import get_session
from ..models import FileRecord, KnowledgeBase
from ..schemas import DocumentAddIn, UploadedFileOut
from ..services.ingest import download_from_url, process_pdf, uploads_dir
from ..services.llm import embedding_enabled
from ..services.vector_store import vector_store_enabled

router = APIRouter()


@router.post("/api/documents", response_model=UploadedFileOut)
async def add_document(
    background: BackgroundTasks,
    payload: DocumentAddIn,
):
    kb_id = payload.knowledge_base_id.strip()
    file_url = payload.file_url.strip()
    file_name = payload.file_name.strip()

    if not file_url:
        raise HTTPException(status_code=400, detail="file_url required")
    if not file_name:
        raise HTTPException(status_code=400, detail="file_name required")
    if not embedding_enabled():
        raise HTTPException(status_code=400, detail="DEEPSEEK_API_KEY required")
    if not vector_store_enabled():
        raise HTTPException(status_code=400, detail="QDRANT_URL required")

    file_id = os.urandom(16).hex()
    out_path = uploads_dir() / f"{file_id}.pdf"

    with get_session() as session:
        kb = session.get(KnowledgeBase, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="knowledge base not found")

        try:
            await download_from_url(url=file_url, out_path=out_path)
        except Exception:
            raise HTTPException(status_code=400, detail="download failed, check file_url")

        rec = FileRecord(
            id=file_id,
            knowledge_base_id=kb_id,
            file_name=file_name,
            storage_path=str(out_path),
            status="processing",
        )
        session.add(rec)

    background.add_task(process_pdf, file_id)
    return UploadedFileOut(id=file_id, file_name=file_name, status="processing")
