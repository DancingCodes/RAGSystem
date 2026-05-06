from __future__ import annotations

import os
from typing import Any

import httpx


def _env(name: str) -> str:
  return os.getenv(name, "").strip()


def llm_enabled() -> bool:
  return bool(_env("OPENAI_API_KEY") and _env("OPENAI_MODEL"))


async def generate_answer(*, question: str, context: str) -> str | None:
  if not llm_enabled():
    return None

  base_url = _env("OPENAI_BASE_URL") or "https://api.openai.com/v1"
  if base_url.endswith("/"):
    base_url = base_url[:-1]
  model = _env("OPENAI_MODEL")
  api_key = _env("OPENAI_API_KEY")

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

