"""
Supabase async client singleton.
Uses supabase-py v2 which supports async operations.

Fix: asyncio.Lock prevents a race condition where two coroutines
could simultaneously create duplicate client instances on startup.
"""
from __future__ import annotations

import asyncio
import logging

from supabase import AClient as AsyncClient, acreate_client

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None
_lock = asyncio.Lock()


async def get_supabase() -> AsyncClient | None:
    """Return a cached async Supabase client, or None if credentials are missing."""
    global _client
    if _client is not None:
        return _client

    async with _lock:
        # Double-checked locking: re-test after acquiring lock
        if _client is not None:
            return _client

        cfg = get_settings()
        if not cfg.supabase_url or not cfg.supabase_key:
            logger.warning("SUPABASE_URL or SUPABASE_KEY missing — using in-memory store.")
            return None
        try:
            _client = await acreate_client(cfg.supabase_url, cfg.supabase_key)
        except Exception as e:
            logger.warning("Supabase connection failed (%s) — falling back to in-memory store.", e)
            return None

    return _client


def reset_client() -> None:
    """Reset the singleton — used in tests to force re-connection."""
    global _client
    _client = None
