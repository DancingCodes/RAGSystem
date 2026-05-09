from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import Base, engine
from .routes.chat import router as chat_router
from .routes.files import router as files_router
from .routes.knowledge_bases import router as knowledge_bases_router
from .response import fail

Base.metadata.create_all(bind=engine)
app = FastAPI(title="RAGSystem API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):
    return JSONResponse(status_code=200, content=fail(str(exc)))


app.include_router(knowledge_bases_router)
app.include_router(files_router)
app.include_router(chat_router)
