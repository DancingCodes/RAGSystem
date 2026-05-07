import math
import os
from typing import Any, Optional

import httpx


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _deepseek_base_url() -> str:
    base_url = "https://api.deepseek.com/v1"
    return base_url[:-1] if base_url.endswith("/") else base_url


def embedding_enabled() -> bool:
    return bool(_env("DEEPSEEK_API_KEY"))


def embedding_model() -> str:
    return "deepseek-embedding"


def chat_model() -> str:
    return "deepseek-chat"


def _normalize(vec: list[float]) -> list[float]:
    s = 0.0
    for v in vec:
        s += float(v) * float(v)
    n = math.sqrt(s)
    if n <= 0:
        return vec
    return [float(v) / n for v in vec]


async def generate_answer(*, question: str, context: str) -> Optional[str]:
    if not embedding_enabled():
        return None

    base_url = _deepseek_base_url()
    model = chat_model()
    api_key = _env("DEEPSEEK_API_KEY")

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
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            res.raise_for_status()
            data = res.json()
            content = data["choices"][0]["message"]["content"]
            return content if isinstance(content, str) else None
    except Exception:
        return None


async def embed_texts(*, texts: list[str]) -> Optional[list[list[float]]]:
    if not embedding_enabled():
        return None

    base_url = _deepseek_base_url()
    api_key = _env("DEEPSEEK_API_KEY")
    model = embedding_model()
    payload: dict[str, Any] = {"model": model, "input": texts}

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(
                f"{base_url}/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            res.raise_for_status()
            data = res.json()
    except Exception:
        return None

    items = data.get("data")
    if not isinstance(items, list):
        return None

    out: list[list[float]] = []
    for it in items:
        emb = it.get("embedding") if isinstance(it, dict) else None
        if not isinstance(emb, list):
            return None
        out.append(_normalize([float(x) for x in emb]))
    return out
