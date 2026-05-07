from __future__ import annotations  # 延迟解析类型注解
#
import os  # 生成随机文件 ID
#
from fastapi import (  # FastAPI 相关组件
  APIRouter,  # 路由器
  BackgroundTasks,  # 后台任务
  File,  # 文件入参声明
  Form,  # 表单入参声明
  HTTPException,  # HTTP 异常
  UploadFile,  # 上传文件类型
)  # import 结束
#
from .db import get_session  # 数据库会话
from .ingest import process_pdf, save_upload, uploads_dir  # 入库流程与落盘
from .llm import embedding_enabled  # embedding 是否启用
from .models import FileRecord, KnowledgeBase  # ORM 模型
from .schemas import UploadedFileOut  # 响应结构
from .vector_store import vector_store_enabled  # 向量库是否启用
#
#
router = APIRouter()  # 创建路由器
#
#
@router.post("/api/files", response_model=UploadedFileOut)  # 上传文件接口
async def upload_file(  # 上传处理函数
  background: BackgroundTasks,  # FastAPI 注入的后台任务队列
  knowledge_base_id: str = Form(...),  # 表单字段：知识库 ID
  file: UploadFile = File(...),  # 表单字段：PDF 文件
):  # 参数结束
  if not knowledge_base_id.strip():  # 校验知识库 ID 非空
    raise HTTPException(status_code=400, detail="knowledge_base_id required")  # 返回 400
  if file.content_type not in (None, "", "application/pdf"):  # 限制文件类型
    raise HTTPException(status_code=400, detail="only pdf supported")  # 返回 400
  if not embedding_enabled():  # 未配置 embedding
    raise HTTPException(status_code=400, detail="DEEPSEEK_API_KEY required")  # 返回 400
  if not vector_store_enabled():  # 未配置向量库
    raise HTTPException(status_code=400, detail="QDRANT_URL required")  # 返回 400
#
  file_id = os.urandom(16).hex()  # 生成文件 ID
  uploads = uploads_dir()  # 获取上传目录
  out_path = uploads / f"{file_id}.pdf"  # 生成落盘路径
#
  with get_session() as session:  # 打开会话
    kb = session.get(KnowledgeBase, knowledge_base_id)  # 校验知识库存在
    if not kb:  # 知识库不存在
      raise HTTPException(status_code=404, detail="knowledge base not found")  # 返回 404
#
    await save_upload(file_obj=file, out_path=out_path)  # 将上传内容保存到磁盘
#
    rec = FileRecord(  # 构造文件记录
      id=file_id,  # 文件 ID
      knowledge_base_id=knowledge_base_id,  # 所属知识库
      file_name=file.filename or "unknown.pdf",  # 原始文件名
      storage_path=str(out_path),  # 存储路径
      status="processing",  # 初始状态
    )  # FileRecord 结束
    session.add(rec)  # 写入数据库
#
  background.add_task(process_pdf, file_id)  # 异步触发 PDF 入库处理
  return UploadedFileOut(  # 返回上传响应
    id=file_id,  # 文件 ID
    file_name=file.filename or "unknown.pdf",  # 文件名
    status="processing",  # 状态
  )  # 响应结束
