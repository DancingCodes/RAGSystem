from __future__ import annotations  # 延迟解析类型注解
#
import shutil  # 复制文件流到磁盘
from pathlib import Path  # 路径处理
#
from .db import get_session  # 数据库会话
from .llm import embed_texts, embedding_enabled  # embedding 调用与开关
from .models import Chunk, FileRecord  # ORM 模型
from .pdf_ingest import chunk_text, extract_pdf_pages  # PDF 抽取与切分
from .vector_store import (  # 向量库操作
  build_point,  # 构造 point
  ensure_collection,  # 确保 collection 存在
  upsert_points,  # upsert 到 Qdrant
  vector_store_enabled,  # 向量库开关
)  # import 结束
#
#
def uploads_dir() -> Path:  # 获取上传目录（并确保存在）
  base_dir = Path(__file__).resolve().parents[1]  # backend/ 根目录
  data_dir = base_dir / "data"  # data 目录
  uploads = data_dir / "uploads"  # uploads 目录
  uploads.mkdir(parents=True, exist_ok=True)  # 创建目录（不存在则创建）
  return uploads  # 返回路径
#
#
async def save_upload(*, file_obj, out_path: Path) -> None:  # 保存上传文件到指定路径
  with out_path.open("wb") as f:  # 以二进制写入打开
    await file_obj.seek(0)  # 确保文件指针回到开头
    shutil.copyfileobj(file_obj.file, f)  # 将上传流拷贝到磁盘文件
#
#
async def process_pdf(file_id: str) -> None:  # 处理一个已上传的 PDF（入库 + 向量化）
  with get_session() as session:  # 打开会话
    file_row = session.get(FileRecord, file_id)  # 读取文件记录
    if not file_row:  # 记录不存在
      return  # 直接返回
    kb_id = file_row.knowledge_base_id  # 知识库 ID
    path = file_row.storage_path  # PDF 存储路径
    file_name = file_row.file_name  # 原始文件名
#
    try:  # 捕获解析/入库异常
      pages = extract_pdf_pages(path)  # 抽取每页文本
      chunk_count = 0  # 统计 chunk 数
      added: list[Chunk] = []  # 保存新增 chunk 行
      for page_number, text in pages:  # 遍历页
        chunks = chunk_text(text)  # 切分为 chunk
        for idx, c in enumerate(chunks):  # 遍历页内 chunk
          row = Chunk(  # 构造 chunk 行
            knowledge_base_id=kb_id,  # 所属知识库
            file_id=file_id,  # 所属文件
            page_number=page_number,  # 页码
            chunk_index=idx,  # 序号
            text=c,  # 文本内容
          )  # Chunk 结束
          session.add(row)  # 写入会话
          added.append(row)  # 记录新增行
          chunk_count += 1  # 数量累加
#
      session.flush()  # 提前落库以获取自增主键 id
#
      if embedding_enabled() and vector_store_enabled() and added:  # embedding 与向量库都可用且有数据
        batch_size = 64  # embedding 批大小
        for start in range(0, len(added), batch_size):  # 分批处理
          batch = added[start : start + batch_size]  # 当前批次
          vectors = await embed_texts(texts=[x.text for x in batch])  # 批量向量化
          if not vectors or len(vectors) != len(batch):  # 向量缺失或数量不匹配
            continue  # 跳过该批（保留文本入库结果）
          ensure_collection(vector_size=len(vectors[0]))  # 确保 collection 维度一致
          points = [  # 构造 upsert 点
            build_point(  # 组装 payload + vector
              chunk_id=int(row.id),  # 以 chunk 主键作为 point id
              vector=vec,  # 向量
              knowledge_base_id=kb_id,  # 用于过滤的字段
              file_id=file_id,  # 文件 ID
              file_name=file_name,  # 文件名
              page_number=int(row.page_number),  # 页码
              chunk_index=int(row.chunk_index),  # 序号
              text=str(row.text),  # 原文
            )  # build_point 结束
            for row, vec in zip(batch, vectors)  # 对齐 chunk 与向量
          ]  # points 结束
          upsert_points(points=points)  # 写入向量库
#
      file_row.status = "succeeded" if chunk_count > 0 else "failed"  # 根据是否产出 chunk 更新状态
      session.add(file_row)  # 持久化状态变更
    except Exception:  # 任意异常视为失败
      file_row.status = "failed"  # 标记失败
      session.add(file_row)  # 持久化失败状态
      raise  # 继续抛出便于观察日志
