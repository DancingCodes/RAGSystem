from __future__ import annotations

import re
from typing import Iterable

from pypdf import PdfReader


_re_ws = re.compile(r"[ \t]+")
_re_many_nl = re.compile(r"\n{3,}")


def extract_pdf_pages(path: str) -> list[tuple[int, str]]:
  reader = PdfReader(path)
  pages: list[tuple[int, str]] = []
  for i, page in enumerate(reader.pages, start=1):
    text = page.extract_text() or ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _re_ws.sub(" ", text)
    text = _re_many_nl.sub("\n\n", text).strip()
    pages.append((i, text))
  return pages


def chunk_text(
  text: str,
  *,
  target_size: int = 900,
  overlap: int = 120,
) -> list[str]:
  if not text:
    return []

  paras = [p.strip() for p in text.split("\n\n") if p.strip()]
  if not paras:
    return []

  chunks: list[str] = []
  buf: list[str] = []
  cur_len = 0

  def flush():
    nonlocal buf, cur_len
    if not buf:
      return
    chunk = "\n\n".join(buf).strip()
    if chunk:
      chunks.append(chunk)
    buf = []
    cur_len = 0

  for p in paras:
    p_len = len(p)
    if p_len > target_size:
      flush()
      for s in _split_long(p, target_size=target_size, overlap=overlap):
        chunks.append(s)
      continue

    if cur_len + p_len + (2 if buf else 0) <= target_size:
      buf.append(p)
      cur_len += p_len + (2 if buf else 0)
    else:
      flush()
      buf.append(p)
      cur_len = p_len

  flush()
  return _apply_overlap(chunks, overlap=overlap)


def _split_long(text: str, *, target_size: int, overlap: int) -> Iterable[str]:
  step = max(1, target_size - overlap)
  i = 0
  n = len(text)
  while i < n:
    yield text[i : i + target_size].strip()
    i += step


def _apply_overlap(chunks: list[str], *, overlap: int) -> list[str]:
  if overlap <= 0 or len(chunks) <= 1:
    return chunks
  out: list[str] = []
  prev_tail = ""
  for c in chunks:
    if prev_tail:
      out.append((prev_tail + c).strip())
    else:
      out.append(c)
    prev_tail = c[-overlap:] if len(c) > overlap else c
  return out

