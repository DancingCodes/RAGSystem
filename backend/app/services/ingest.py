from pathlib import Path
from typing import Any

import httpx

from ..db import get_session
from ..models import Chunk, FileRecord
from .llm import embed_texts, embedding_enabled
from .pdf_ingest import chunk_text, extract_pdf_pages
from .vector_store import build_point, ensure_collection, upsert_points, vector_store_enabled


async def batch_embed_and_upsert(items: list[dict[str, Any]]) -> int:
    """批处理 embedding 并写入向量库。items 需包含 chunk_id/text/knowledge_base_id/file_id/file_name/page_number/chunk_index。"""
    if not items:
        return 0

    batch_size = 64
    embedded = 0
    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        texts = [item["text"] for item in batch]
        vectors = await embed_texts(texts=texts)
        if not vectors or len(vectors) != len(batch):
            continue

        ensure_collection(vector_size=len(vectors[0]))
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


async def download_from_url(*, url: str, out_path: Path) -> None:
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        res = await client.get(url)
        res.raise_for_status()
        out_path.write_bytes(res.content)


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

      file_row.status = "succeeded" if chunk_count > 0 else "failed"
      session.add(file_row)
    except Exception:
      file_row.status = "failed"
      session.add(file_row)
      raise

