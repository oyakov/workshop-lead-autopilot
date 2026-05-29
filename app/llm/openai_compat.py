"""OpenAI-compatible client — LM Studio / OpenAI / any compat endpoint."""
from __future__ import annotations

from openai import AsyncOpenAI

from app.config import get_settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        cfg = get_settings()
        _client = AsyncOpenAI(
            base_url=cfg.llm_base_url,
            api_key=cfg.llm_api_key,
        )
    return _client


async def chat(messages: list[dict], max_tokens: int = 512) -> str:
    cfg = get_settings()
    client = _get_client()
    resp = await client.chat.completions.create(
        model=cfg.llm_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()
