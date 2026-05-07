# 已人工审读

import datetime as dt
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# 知识库表
class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    # 知识库 ID
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # 知识库名称
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # 创建时间
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )


# 上传文件表
class FileRecord(Base):
    __tablename__ = "files"
    # 文件 ID
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # 关联的知识库 ID
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_bases.id"),
        index=True,
        nullable=False,
    )
    # 原始文件名
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    # 本地存储路径
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    # 处理状态
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    # 创建时间
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )


# 文本切片表
class Chunk(Base):
    __tablename__ = "chunks"
    # 自增主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 所属知识库
    knowledge_base_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    # 所属文件
    file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("files.id"), index=True, nullable=False
    )
    # 页码（从 1 开始）
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # 页内切片序号
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # 切片原文
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # 创建时间
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
