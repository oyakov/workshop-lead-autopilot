"""Gemini API client via google-generativeai."""
from __future__ import annotations

import logging

import google.generativeai as genai

from app.config import get_settings

logger = logging.getLogger(__name__)

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        cfg = get_settings()
        genai.configure(api_key=cfg.gemini_api_key)
        _configured = True


async def chat(messages: list[dict], max_tokens: int = 512) -> str:
    """
    Call Gemini API. messages format: [{"role": "user", "content": "..."}]
    Converts to Gemini format internally.
    """
    _ensure_configured()
    cfg = get_settings()

    model = genai.GenerativeModel(cfg.gemini_model)

    # Convert OpenAI-style messages to Gemini format
    gemini_parts = []
    for msg in messages:
        role = "user" if msg["role"] in ("user", "system") else "model"
        gemini_parts.append({"role": role, "parts": [msg["content"]]})

    # Merge system + user if both present as first two messages
    if len(gemini_parts) >= 2 and gemini_parts[0]["role"] == "user" and gemini_parts[1]["role"] == "user":
        combined = gemini_parts[0]["parts"][0] + "\n\n" + gemini_parts[1]["parts"][0]
        gemini_parts = [{"role": "user", "parts": [combined]}] + gemini_parts[2:]

    response = await model.generate_content_async(
        gemini_parts,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.3,
        ),
    )
    return response.text.strip()
