"""
Supabase async client singleton.
Uses supabase-py v2 which supports async operations.
"""
from __future__ import annotations

from functools import lru_cache

from supabase import AClient as AsyncClient, acreate_client

from app.config import get_settings

_client: AsyncClient | None = None


async def get_supabase() -> AsyncClient:
    """Return a cached async Supabase client."""
    global _client
    if _client is None:
        cfg = get_settings()
        _client = await acreate_client(cfg.supabase_url, cfg.supabase_key)
    return _client
