from __future__ import annotations

from dataclasses import dataclass

from rank_bm25 import BM25Okapi


@dataclass(frozen=True)
class RetrievedChunk:
  file_name: str
  page_number: int
  text: str
  score: float


def _tokenize(s: str) -> list[str]:
  return [t for t in s.lower().replace("\n", " ").split(" ") if t]


def retrieve_top_k(
  *,
  question: str,
  texts: list[str],
  metas: list[tuple[str, int]],
  top_k: int,
) -> list[RetrievedChunk]:
  if not texts:
    return []

  corpus = [_tokenize(t) for t in texts]
  bm25 = BM25Okapi(corpus)
  scores = bm25.get_scores(_tokenize(question))

  idxs = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)[:top_k]
  out: list[RetrievedChunk] = []
  for i in idxs:
    score = float(scores[i])
    if score <= 0:
      continue
    file_name, page_number = metas[int(i)]
    out.append(
      RetrievedChunk(
        file_name=file_name,
        page_number=page_number,
        text=texts[int(i)],
        score=score,
      )
    )
  return out
