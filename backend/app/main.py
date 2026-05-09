from fastapi import FastAPI

from .data.db import Base, engine
from .routes.chat import router as chat_router
from .routes.files import router as files_router
from .routes.knowledge_bases import router as knowledge_bases_router

Base.metadata.create_all(bind=engine)
app = FastAPI(title="RAGSystem API")

app.include_router(knowledge_bases_router)
app.include_router(files_router)
app.include_router(chat_router)
