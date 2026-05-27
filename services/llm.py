"""Shared LLM client — points to LM Studio (OpenAI-compatible) or any OpenAI-compat endpoint."""
import os
from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url=os.environ.get("LLM_BASE_URL", "http://localhost:1234/v1"),
            api_key=os.environ.get("LLM_API_KEY", "lm-studio"),
        )
    return _client


def model() -> str:
    return os.environ.get("LLM_MODEL", "google/gemma-e4b")


async def chat(messages: list[dict], max_tokens: int = 200) -> str:
    client = get_client()
    resp = await client.chat.completions.create(
        model=model(),
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()
