import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any, Optional

import httpx
from sentence_transformers import SentenceTransformer

from ..utils.env import env

_embedding_model: Optional[SentenceTransformer] = None


def _get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    model = _embedding_model
    if model is not None:
        return model
    model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    _embedding_model = model
    return model


def chat_enabled() -> bool:
    return bool(env("DEEPSEEK_API_KEY"))


def _deepseek_base_url() -> str:
    base_url = "https://api.deepseek.com/v1"
    return base_url[:-1] if base_url.endswith("/") else base_url


def chat_model() -> str:
    return "deepseek-chat"



async def generate_answer_stream(
    *, question: str, context: str
) -> AsyncGenerator[str | None, None]:
    """Stream answer tokens from DeepSeek API."""
    if not chat_enabled():
        yield None
        return

    base_url = _deepseek_base_url()
    model = chat_model()
    api_key = env("DEEPSEEK_API_KEY")

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是一个检索增强问答助手。只允许依据给定的资料片段回答；资料不足时明确说明未找到依据。",
            },
            {
                "role": "user",
                "content": f"问题：{question}\n\n资料片段：\n{context}",
            },
        ],
        "temperature": 0.2,
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        token = delta.get("content")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    except httpx.HTTPError:
        yield None


async def embed_texts(*, texts: list[str]) -> list[list[float]]:
    model = _get_embedding_model()
    embeddings = await asyncio.to_thread(model.encode, texts, normalize_embeddings=True)
    return [vec.tolist() for vec in embeddings]
