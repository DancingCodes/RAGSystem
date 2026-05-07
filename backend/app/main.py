from __future__ import annotations

from pathlib import Path

try:
  from dotenv import load_dotenv
except Exception:
  load_dotenv = None

if load_dotenv:
  load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routes_chat import router as chat_router
from .routes_files import router as files_router
from .routes_health import router as health_router
from .routes_knowledge_bases import router as knowledge_bases_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="RAGSystem API")

app.add_middleware(
  CORSMiddleware,
  allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
  ],
  allow_origin_regex=r"^http://192\.168\.\d+\.\d+:3000$",
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(knowledge_bases_router)
app.include_router(files_router)
app.include_router(chat_router)
