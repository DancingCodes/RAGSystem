from __future__ import annotations  # 延迟解析类型注解
#
import math  # 数学计算（归一化）
import os  # 读取环境变量
from typing import Any, Optional  # 通用类型与可选类型
#
import httpx  # HTTP 客户端
#
#
def _env(name: str) -> str:  # 读取并清理环境变量
  return os.getenv(name, "").strip()  # 取值并去空白
#
#
def _deepseek_base_url() -> str:  # 获取 DeepSeek API 基地址
  base_url = "https://api.deepseek.com/v1"  # OpenAI 兼容路径前缀
  return base_url[:-1] if base_url.endswith("/") else base_url  # 去掉尾部斜杠
#
#
def embedding_enabled() -> bool:  # 是否启用 embedding/LLM
  return bool(_env("DEEPSEEK_API_KEY"))  # 以是否配置 API Key 判断
#
#
def embedding_model() -> str:  # embedding 模型名
  return "deepseek-embedding"  # DeepSeek embedding
#
#
def chat_model() -> str:  # chat 模型名
  return "deepseek-chat"  # DeepSeek chat
#
#
def _normalize(vec: list[float]) -> list[float]:  # L2 归一化向量
  s = 0.0  # 平方和
  for v in vec:  # 遍历每个维度
    s += float(v) * float(v)  # 累加平方
  n = math.sqrt(s)  # 求范数
  if n <= 0:  # 防止除零
    return vec  # 原样返回
  return [float(v) / n for v in vec]  # 返回归一化结果
#
#
async def generate_answer(*, question: str, context: str) -> Optional[str]:  # 调用 LLM 生成答案
  if not embedding_enabled():  # 未配置 API Key
    return None  # 直接返回空
#
  base_url = _deepseek_base_url()  # API 基地址
  model = chat_model()  # 模型名
  api_key = _env("DEEPSEEK_API_KEY")  # API Key
#
  payload: dict[str, Any] = {  # OpenAI 兼容的请求体
    "model": model,  # 模型字段
    "messages": [  # 对话消息
      {  # system prompt
        "role": "system",  # system 角色
        "content": "你是一个检索增强问答助手。只允许依据给定的资料片段回答；资料不足时明确说明未找到依据。",  # 行为约束
      },  # system 结束
      {  # user 输入
        "role": "user",  # user 角色
        "content": f"问题：{question}\n\n资料片段：\n{context}",  # 把检索片段拼进输入
      },  # user 结束
    ],  # messages 结束
    "temperature": 0.2,  # 控制随机性
  }  # payload 结束
#
  try:  # 捕获网络/解析错误
    async with httpx.AsyncClient(timeout=60) as client:  # 创建异步客户端
      res = await client.post(  # 发起 POST 请求
        f"{base_url}/chat/completions",  # chat 端点
        headers={"Authorization": f"Bearer {api_key}"},  # 鉴权头
        json=payload,  # JSON 请求体
      )  # post 结束
      res.raise_for_status()  # 非 2xx 则抛异常
      data = res.json()  # 解析 JSON 响应
      content = data["choices"][0]["message"]["content"]  # 取第一条回答
      return content if isinstance(content, str) else None  # 返回字符串回答
  except Exception:  # 任意异常
    return None  # 统一返回空（上层转成 502）
#
#
async def embed_texts(*, texts: list[str]) -> Optional[list[list[float]]]:  # 批量文本向量化
  if not embedding_enabled():  # 未配置 API Key
    return None  # 直接返回空
#
  base_url = _deepseek_base_url()  # API 基地址
  api_key = _env("DEEPSEEK_API_KEY")  # API Key
  model = embedding_model()  # embedding 模型名
  payload: dict[str, Any] = {"model": model, "input": texts}  # OpenAI 兼容请求体
#
  try:  # 捕获网络/解析错误
    async with httpx.AsyncClient(timeout=60) as client:  # 创建异步客户端
      res = await client.post(  # 发起 POST 请求
        f"{base_url}/embeddings",  # embedding 端点
        headers={"Authorization": f"Bearer {api_key}"},  # 鉴权头
        json=payload,  # JSON 请求体
      )  # post 结束
      res.raise_for_status()  # 非 2xx 则抛异常
      data = res.json()  # 解析 JSON 响应
  except Exception:  # 任意异常
    return None  # 统一返回空
#
  items = data.get("data")  # 读取 data 字段
  if not isinstance(items, list):  # 必须是列表
    return None  # 格式异常则返回空
#
  out: list[list[float]] = []  # 输出向量列表
  for it in items:  # 遍历每条 embedding
    emb = it.get("embedding") if isinstance(it, dict) else None  # 取 embedding 字段
    if not isinstance(emb, list):  # embedding 必须是列表
      return None  # 格式异常则返回空
    out.append(_normalize([float(x) for x in emb]))  # 转 float 并归一化
  return out  # 返回向量列表
