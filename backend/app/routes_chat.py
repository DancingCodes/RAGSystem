from __future__ import annotations  # 延迟解析类型注解
#
from fastapi import APIRouter, HTTPException  # 路由器与 HTTP 异常
#
from .db import get_session  # 数据库会话
from .llm import embed_texts, embedding_enabled, generate_answer  # embedding 与 LLM 调用
from .models import KnowledgeBase  # 知识库模型
from .schemas import ChatIn, ChatOut  # 请求/响应结构
from .vector_store import search, vector_store_enabled  # 向量检索与开关
#
#
router = APIRouter()  # 创建路由器
#
#
@router.post("/api/chat", response_model=ChatOut)  # 问答接口
async def chat_api(payload: ChatIn):  # 问答处理函数
  kb_id = payload.knowledge_base_id.strip()  # 清理知识库 ID
  question = payload.question.strip()  # 清理问题文本
  if not kb_id:  # 必须提供知识库 ID
    raise HTTPException(status_code=400, detail="knowledge_base_id required")  # 返回 400
  if not question:  # 必须提供问题
    raise HTTPException(status_code=400, detail="question required")  # 返回 400
#
  if not embedding_enabled():  # 未配置 embedding
    raise HTTPException(status_code=400, detail="DEEPSEEK_API_KEY required")  # 返回 400
  if not vector_store_enabled():  # 未配置向量库
    raise HTTPException(status_code=400, detail="QDRANT_URL required")  # 返回 400
#
  kb_name = ""  # 用于提示信息
  with get_session() as session:  # 打开会话
    kb = session.get(KnowledgeBase, kb_id)  # 查询知识库
    if not kb:  # 不存在
      raise HTTPException(status_code=404, detail="knowledge base not found")  # 返回 404
    kb_name = kb.name  # 记录名称
#
  qvecs = await embed_texts(texts=[question])  # 对问题做 embedding
  if not qvecs:  # embedding 失败
    raise HTTPException(status_code=502, detail="embedding failed")  # 返回 502
#
  hits = search(knowledge_base_id=kb_id, query_vector=qvecs[0], limit=payload.top_k) or []  # 检索 top_k
  retrieved = [  # 将命中结果整理成结构化列表
    {  # 每条命中
      "file_name": str(h.payload.get("file_name") or ""),  # 文件名
      "page_number": int(h.payload.get("page_number") or 0),  # 页码
      "text": str(h.payload.get("text") or ""),  # 命中文本
      "score": float(h.score),  # 相似度分数
    }  # 单条结束
    for h in hits  # 遍历所有命中
    if (h.payload.get("file_name") and h.payload.get("text"))  # 过滤无效 payload
  ]  # retrieved 结束
#
  if not retrieved:  # 未检索到片段
    return ChatOut(  # 直接返回提示
      answer=f"当前知识库「{kb_name}」未检索到相关片段，建议换个问法或确认 PDF 是否已成功入库。",  # 友好提示
      citations=[],  # 无引用
    )  # 响应结束
#
  context = "\n\n".join(  # 拼接给 LLM 的上下文
    [  # 列表推导式
      f"[{i+1}] 文件：{c['file_name']}；页码：{c['page_number']}\n{c['text']}"  # 带编号的片段
      for i, c in enumerate(retrieved)  # 遍历片段并编号
    ]  # 列表结束
  )  # join 结束
  llm = await generate_answer(question=question, context=context)  # 调用 LLM 生成回答
  if not llm:  # 生成失败
    raise HTTPException(status_code=502, detail="llm generate failed")  # 返回 502
  answer = llm  # 保存回答文本
#
  citations = [  # 构造引用返回
    {"file_name": c["file_name"], "page_number": c["page_number"], "text": c["text"][:500]}  # 截断引用文本
    for c in retrieved  # 遍历片段
  ]  # citations 结束
  return ChatOut(answer=answer, citations=citations)  # 返回最终响应
