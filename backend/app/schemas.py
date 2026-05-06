from __future__ import annotations

from pydantic import BaseModel, Field


class KnowledgeBaseOut(BaseModel):
  id: str
  name: str


class KnowledgeBaseCreateIn(BaseModel):
  name: str = Field(min_length=1, max_length=200)


class UploadedFileOut(BaseModel):
  id: str
  file_name: str
  status: str | None = None


class ChatIn(BaseModel):
  knowledge_base_id: str = Field(min_length=1)
  question: str = Field(min_length=1)
  top_k: int = Field(default=5, ge=1, le=20)


class CitationOut(BaseModel):
  file_name: str
  page_number: int | None = None
  text: str | None = None


class ChatOut(BaseModel):
  answer: str
  citations: list[CitationOut] = []

