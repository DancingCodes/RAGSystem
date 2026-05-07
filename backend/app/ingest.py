import shutil
from pathlib import Path
from .db import get_session
from .llm import embed_texts, embedding_enabled
from .models import Chunk, FileRecord
from .pdf_ingest import chunk_text, extract_pdf_pages
from .vector_store import (
    build_point,
    ensure_collection,
    upsert_points,
    vector_store_enabled,
)


def uploads_dir() -> Path:
    base_dir = Path(__file__).resolve().parents[1]
    data_dir = base_dir / "data"
    uploads = data_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    return uploads


async def save_upload(*, file_obj, out_path: Path) -> None:
    with out_path.open("wb") as f:
        await file_obj.seek(0)
        shutil.copyfileobj(file_obj.file, f)


async def process_pdf(file_id: str) -> None:
    with get_session() as session:
        file_row = session.get(FileRecord, file_id)
        if not file_row:
            return
        kb_id = file_row.knowledge_base_id
        path = file_row.storage_path
        file_name = file_row.file_name
        try:
            pages = extract_pdf_pages(path)
            chunk_count = 0
            added: list[Chunk] = []
            for page_number, text in pages:
                chunks = chunk_text(text)
                for idx, c in enumerate(chunks):
                    row = Chunk(
                        knowledge_base_id=kb_id,
                        file_id=file_id,
                        page_number=page_number,
                        chunk_index=idx,
                        text=c,
                    )
                    session.add(row)
                    added.append(row)
                    chunk_count += 1
            session.flush()
            if embedding_enabled() and vector_store_enabled() and added:
                batch_size = 64
                for start in range(0, len(added), batch_size):
                    batch = added[start : start + batch_size]
                    vectors = await embed_texts(texts=[x.text for x in batch])
                    if not vectors or len(vectors) != len(batch):
                        continue
                    ensure_collection(vector_size=len(vectors[0]))
                    points = [
                        build_point(
                            chunk_id=int(row.id),
                            vector=vec,
                            knowledge_base_id=kb_id,
                            file_id=file_id,
                            file_name=file_name,
                            page_number=int(row.page_number),
                            chunk_index=int(row.chunk_index),
                            text=str(row.text),
                        )
                        for row, vec in zip(batch, vectors)
                    ]
                    upsert_points(points=points)
            file_row.status = "succeeded" if chunk_count > 0 else "failed"
            session.add(file_row)
        except Exception:
            file_row.status = "failed"
            session.add(file_row)
            raise
