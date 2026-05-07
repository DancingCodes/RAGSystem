from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from .db import Base, engine

from .routes.chat import router as chat_router
from .routes.files import router as files_router
from .routes.health import router as health_router
from .routes.knowledge_bases import router as knowledge_bases_router

Base.metadata.create_all(bind=engine)
app = FastAPI(title="RAGSystem API")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(knowledge_bases_router)
app.include_router(files_router)
app.include_router(chat_router)
