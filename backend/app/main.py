from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine

from .routes_chat import router as chat_router
from .routes_files import router as files_router
from .routes_health import router as health_router
from .routes_knowledge_bases import router as knowledge_bases_router

# 加载环境变量
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

# 数据库初始化
Base.metadata.create_all(bind=engine)
# 创建 FastAPI 应用
app = FastAPI(title="RAGSystem API")

# 注册中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(health_router)
app.include_router(knowledge_bases_router)
app.include_router(files_router)
app.include_router(chat_router)
