"""Common service-wide helper utilities."""
from __future__ import annotations

from datetime import datetime, timezone


def parse_iso_datetime(iso_str: str) -> datetime:
    """
    Parse an ISO datetime string safely.
    Handles 'Z' suffix normalization to '+00:00'.
    If the string is empty or invalid, returns the current UTC datetime.
    """
    if not iso_str:
        return datetime.now(timezone.utc)
    try:
        cleaned = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except Exception:
        return datetime.now(timezone.utc)
