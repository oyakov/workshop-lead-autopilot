"""
LLM Gateway — routes requests to configured provider with automatic fallback.

Priority:
  1. Primary provider (LLM_PROVIDER env)
  2. Fallback provider (LLM_FALLBACK_PROVIDER env, if set)
  3. Returns empty string — callers must handle gracefully

Supports: gemini | lmstudio | openai
"""
from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


async def _call_provider(provider: str, messages: list[dict], max_tokens: int) -> str:
    if provider == "gemini":
        from app.llm.gemini import chat
        return await chat(messages, max_tokens)
    elif provider in ("lmstudio", "openai"):
        from app.llm.openai_compat import chat
        return await chat(messages, max_tokens)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


async def chat(messages: list[dict], max_tokens: int = 512) -> str:
    """
    Send messages to the configured LLM.
    Automatically falls back to secondary provider on failure.
    """
    cfg = get_settings()
    primary = cfg.llm_provider
    fallback = cfg.llm_fallback_provider

    try:
        result = await _call_provider(primary, messages, max_tokens)
        if result:
            return result
        raise ValueError("Empty response from primary provider")
    except Exception as primary_err:
        logger.warning("LLM primary '%s' failed: %s", primary, primary_err)

        if fallback and fallback != primary:
            try:
                logger.info("Falling back to LLM provider '%s'", fallback)
                result = await _call_provider(fallback, messages, max_tokens)
                if result:
                    return result
            except Exception as fallback_err:
                logger.error("LLM fallback '%s' also failed: %s", fallback, fallback_err)

        return ""
