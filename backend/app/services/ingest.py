from pathlib import Path
from typing import Any

from ..data.db import get_session
from ..data.models import Chunk, FileRecord
from .llm import embed_texts
from .pdf_ingest import chunk_text, extract_pdf_pages
from .vector_store import build_point, ensure_collection, upsert_points, vector_store_enabled


async def batch_embed_and_upsert(items: list[dict[str, Any]]) -> int:
    """批处理 embedding 并写入向量库"""
    if not items:
        return 0

    # Ensure collection exists once before the batch loop
    first_text = items[0]["text"]
    vecs = await embed_texts(texts=[first_text])
    if vecs:
        ensure_collection(vector_size=len(vecs[0]))

    batch_size = 64
    embedded = 0
    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        texts = [item["text"] for item in batch]
        vectors = await embed_texts(texts=texts)
        if not vectors or len(vectors) != len(batch):
            continue

        points = [
            build_point(
                chunk_id=item["chunk_id"],
                vector=vec,
                knowledge_base_id=item["knowledge_base_id"],
                file_id=item["file_id"],
                file_name=item["file_name"],
                page_number=item["page_number"],
                chunk_index=item["chunk_index"],
                text=item["text"],
            )
            for item, vec in zip(batch, vectors)
        ]
        upsert_points(points=points)
        embedded += len(points)

    return embedded


def uploads_dir() -> Path:
    base_dir = Path(__file__).resolve().parents[2]
    data_dir = base_dir / "data"
    uploads = data_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    return uploads


async def process_pdf(file_id: str) -> None:
    # Read metadata in its own session
    with get_session() as session:
        file_row = session.get(FileRecord, file_id)
        if not file_row:
            return
        kb_id = str(file_row.knowledge_base_id)
        path = str(file_row.storage_path)
        file_name = str(file_row.file_name)

    # Extract and chunk outside DB session
    try:
        pages = extract_pdf_pages(path)
        chunk_data: list[dict[str, Any]] = []
        for page_number, text in pages:
            for idx, c in enumerate(chunk_text(text)):
                chunk_data.append({
                    "page_number": page_number,
                    "chunk_index": idx,
                    "text": c,
                })

        # Write chunks in a fresh session (so IDs are auto-generated)
        with get_session() as session:
            file_row = session.get(FileRecord, file_id)
            if not file_row:
                return

            added: list[Chunk] = []
            for item in chunk_data:
                row = Chunk(
                    knowledge_base_id=kb_id,
                    file_id=file_id,
                    page_number=item["page_number"],
                    chunk_index=item["chunk_index"],
                    text=item["text"],
                )
                session.add(row)
                added.append(row)

            session.flush()  # Populate auto-increment IDs

            if vector_store_enabled() and added:
                items = [
                    {
                        "chunk_id": int(row.id),
                        "text": row.text,
                        "knowledge_base_id": kb_id,
                        "file_id": file_id,
                        "file_name": file_name,
                        "page_number": int(row.page_number),
                        "chunk_index": int(row.chunk_index),
                    }
                    for row in added
                ]
                await batch_embed_and_upsert(items)

            file_row.status = "succeeded" if chunk_data else "failed"

    except Exception:
        # Write failed status in a separate session so the rollback
        # from the main session does not discard it
        with get_session() as session:
            fr = session.get(FileRecord, file_id)
            if fr:
                fr.status = "failed"
        raise
