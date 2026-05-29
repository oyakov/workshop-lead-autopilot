"""
Supabase async client singleton.
Uses supabase-py v2 which supports async operations.
"""
from __future__ import annotations

from functools import lru_cache

from supabase import AClient as AsyncClient, acreate_client

from app.config import get_settings

import logging

logger = logging.getLogger(__name__)
_client: AsyncClient | None = None


async def get_supabase() -> AsyncClient | None:
    """Return a cached async Supabase client, or None if credentials are missing/invalid."""
    global _client
    if _client is None:
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
