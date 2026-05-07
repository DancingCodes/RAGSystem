from __future__ import annotations  # 延迟解析类型注解
#
import os  # 读取环境变量
from dataclasses import dataclass  # 数据类
from typing import Any, Optional  # 通用类型与可选类型
#
from qdrant_client import QdrantClient  # Qdrant 客户端
from qdrant_client.http.models import (  # Qdrant HTTP 模型
  Distance,  # 距离度量
  FieldCondition,  # 字段过滤条件
  Filter,  # 过滤器
  MatchValue,  # 精确匹配值
  PointStruct,  # 点结构
  VectorParams,  # 向量配置
)  # import 结束
#
#
def _env(name: str) -> str:  # 读取并清理环境变量
  return os.getenv(name, "").strip()  # 取值并去空白
#
#
def vector_store_enabled() -> bool:  # 是否启用向量库
  return bool(_env("QDRANT_URL"))  # 以是否配置 URL 判断
#
#
def _collection() -> str:  # 获取 collection 名称
  return _env("QDRANT_COLLECTION") or "rag_chunks"  # 默认 rag_chunks
#
#
def _client() -> QdrantClient:  # 创建 Qdrant 客户端
  url = _env("QDRANT_URL")  # Qdrant 地址
  api_key = _env("QDRANT_API_KEY") or None  # 可选 API Key
  return QdrantClient(url=url, api_key=api_key)  # 返回客户端
#
#
def ensure_collection(*, vector_size: int) -> None:  # 确保 collection 存在且维度一致
  client = _client()  # 创建客户端
  name = _collection()  # collection 名
  collections = client.get_collections().collections  # 获取所有 collection
  if any(c.name == name for c in collections):  # 已存在
    info = client.get_collection(name)  # 读取配置
    cfg = info.config.params.vectors  # 向量配置
    if hasattr(cfg, "size") and int(cfg.size) != int(vector_size):  # 维度不一致
      raise ValueError("Qdrant collection vector size mismatch")  # 抛错提示
    return  # 维度一致则结束
#
  client.create_collection(  # 创建 collection
    collection_name=name,  # 名称
    vectors_config=VectorParams(size=int(vector_size), distance=Distance.COSINE),  # 维度与距离
  )  # create_collection 结束
#
#
@dataclass(frozen=True)  # 不可变数据类
class VectorHit:  # 单条检索命中
  id: int  # point id
  score: float  # 相似度分数
  payload: dict[str, Any]  # payload 元数据
#
#
def upsert_points(*, points: list[PointStruct]) -> None:  # 批量 upsert 点
  client = _client()  # 创建客户端
  client.upsert(collection_name=_collection(), points=points)  # 写入指定 collection
#
#
def build_point(  # 构造一个 Qdrant point
  *,  # 之后必须用关键字传参
  chunk_id: int,  # chunk 主键
  vector: list[float],  # 向量
  knowledge_base_id: str,  # 知识库 ID
  file_id: str,  # 文件 ID
  file_name: str,  # 文件名
  page_number: int,  # 页码
  chunk_index: int,  # chunk 序号
  text: str,  # chunk 文本
) -> PointStruct:  # 返回 point 结构
  payload: dict[str, Any] = {  # 作为检索返回的元数据
    "knowledge_base_id": knowledge_base_id,  # 用于过滤
    "file_id": file_id,  # 文件 ID
    "file_name": file_name,  # 文件名
    "page_number": int(page_number),  # 页码（整数）
    "chunk_index": int(chunk_index),  # 序号（整数）
    "text": text,  # 原文
  }  # payload 结束
  return PointStruct(id=int(chunk_id), vector=vector, payload=payload)  # 构造点并返回
#
#
def search(  # 向量检索
  *,  # 之后必须用关键字传参
  knowledge_base_id: str,  # 过滤用知识库 ID
  query_vector: list[float],  # 查询向量
  limit: int,  # 返回条数
) -> Optional[list[VectorHit]]:  # 返回命中列表或 None
  if not vector_store_enabled():  # 未启用向量库
    return None  # 直接返回空
#
  try:  # 捕获任何 Qdrant 异常
    client = _client()  # 创建客户端
    flt = Filter(  # 构造过滤器
      must=[  # 必须满足
        FieldCondition(  # 字段条件
          key="knowledge_base_id",  # 按知识库过滤
          match=MatchValue(value=str(knowledge_base_id)),  # 精确匹配
        )  # FieldCondition 结束
      ]  # must 结束
    )  # Filter 结束
    res = client.search(  # 发起检索
      collection_name=_collection(),  # 指定 collection
      query_vector=query_vector,  # 查询向量
      query_filter=flt,  # 过滤器
      limit=int(limit),  # top-k
      with_payload=True,  # 返回 payload
    )  # search 结束
    out: list[VectorHit] = []  # 输出命中列表
    for p in res:  # 遍历返回点
      out.append(VectorHit(id=int(p.id), score=float(p.score), payload=dict(p.payload or {})))  # 转成 VectorHit
    return out  # 返回命中列表
  except Exception:  # 任意异常
    return None  # 返回空让上层兜底

