from __future__ import annotations  # 延迟解析类型注解
#
import os  # 生成随机 ID
#
from fastapi import APIRouter, HTTPException  # 路由器与 HTTP 异常
from sqlalchemy import select  # SQL 查询构造器
#
from .db import get_session  # 数据库会话
from .llm import embed_texts, embedding_enabled  # embedding 调用与开关
from .models import Chunk, FileRecord, KnowledgeBase  # ORM 模型
from .schemas import KnowledgeBaseCreateIn, KnowledgeBaseOut  # 请求/响应结构
from .vector_store import (  # 向量库操作
  build_point,  # 构造点
  ensure_collection,  # 确保 collection 存在且维度一致
  upsert_points,  # 写入点
  vector_store_enabled,  # 向量库开关
)  # import 结束
#
#
router = APIRouter()  # 创建路由器
#
#
@router.get("/api/knowledge-bases", response_model=list[KnowledgeBaseOut])  # 列出知识库
def list_knowledge_bases():  # 列表接口
  with get_session() as session:  # 打开会话
    rows = (  # 查询结果集
      session.execute(  # 执行查询
        select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())  # 按创建时间倒序
      )  # 查询构造结束
      .scalars()  # 取出实体
      .all()  # 拉取全部
    )  # rows 赋值结束
    return [KnowledgeBaseOut(id=x.id, name=x.name) for x in rows]  # 转成响应模型
#
#
@router.post("/api/knowledge-bases", response_model=KnowledgeBaseOut)  # 创建知识库
def create_knowledge_base(payload: KnowledgeBaseCreateIn):  # 创建接口
  name = payload.name.strip()  # 去除首尾空白
  if not name:  # 空名称不允许
    raise HTTPException(status_code=400, detail="name required")  # 返回 400
#
  kb_id = os.urandom(16).hex()  # 生成知识库 ID
  kb = KnowledgeBase(id=kb_id, name=name)  # 构造 ORM 实体
  with get_session() as session:  # 打开会话
    session.add(kb)  # 写入数据库
  return KnowledgeBaseOut(id=kb_id, name=name)  # 返回创建结果
#
#
@router.post("/api/knowledge-bases/{knowledge_base_id}/reindex")  # 重建向量索引
async def reindex_knowledge_base(knowledge_base_id: str):  # 重建接口
  kb_id = knowledge_base_id.strip()  # 清理路径参数
  if not kb_id:  # 空 ID 不允许
    raise HTTPException(status_code=400, detail="knowledge_base_id required")  # 返回 400
  if not embedding_enabled():  # 未配置 embedding
    raise HTTPException(status_code=400, detail="DEEPSEEK_API_KEY required")  # 返回 400
  if not vector_store_enabled():  # 未配置向量库
    raise HTTPException(status_code=400, detail="QDRANT_URL required")  # 返回 400
#
  with get_session() as session:  # 打开会话
    kb = session.get(KnowledgeBase, kb_id)  # 读取知识库
    if not kb:  # 不存在
      raise HTTPException(status_code=404, detail="knowledge base not found")  # 返回 404
#
    rows = (  # 查询所有 chunk + 文件信息
      session.execute(  # 执行查询
        select(  # 选择需要的字段
          Chunk.id,  # chunk 主键
          Chunk.text,  # chunk 文本
          Chunk.page_number,  # 页码
          Chunk.chunk_index,  # 序号
          FileRecord.id,  # 文件 ID
          FileRecord.file_name,  # 文件名
        )  # select 字段结束
        .join(FileRecord, FileRecord.id == Chunk.file_id)  # 关联 files
        .where(Chunk.knowledge_base_id == kb_id)  # 只取当前知识库
        .order_by(Chunk.id.asc())  # 按 chunk id 升序
      )  # execute 参数结束
      .all()  # 拉取全部行
    )  # rows 赋值结束
#
    if not rows:  # 没有任何 chunk
      return {"ok": True, "embedded": 0}  # 直接返回
#
    batch_size = 64  # embedding 批大小
    embedded = 0  # 累计写入数量
    for start in range(0, len(rows), batch_size):  # 分批处理
      batch = rows[start : start + batch_size]  # 当前批次
      texts = [str(x[1]) for x in batch]  # 提取文本列
      vectors = await embed_texts(texts=texts)  # 批量获取向量
      if not vectors or len(vectors) != len(batch):  # embedding 失败或数量不匹配
        raise HTTPException(status_code=502, detail="embedding failed")  # 返回 502
#
      ensure_collection(vector_size=len(vectors[0]))  # 确保向量库维度一致
      points = [  # 构造 upsert 点列表
        build_point(  # 组装 Qdrant point
          chunk_id=int(row[0]),  # chunk id 作为 point id
          vector=vec,  # embedding 向量
          knowledge_base_id=kb_id,  # 过滤字段
          file_id=str(row[4]),  # 文件 ID
          file_name=str(row[5]),  # 文件名
          page_number=int(row[2]),  # 页码
          chunk_index=int(row[3]),  # 序号
          text=str(row[1]),  # 原文
        )  # build_point 结束
        for row, vec in zip(batch, vectors)  # 对齐行与向量
      ]  # points 结束
      upsert_points(points=points)  # 写入向量库
      embedded += len(points)  # 计数累加
#
  return {"ok": True, "embedded": embedded}  # 返回统计结果
