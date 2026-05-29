"""Events repository — append-only audit log."""
from __future__ import annotations

from typing import Any

from app.db.client import get_supabase
from app.models.event import EventLog

TABLE = "events"

# Local in-memory list for fallback execution
_in_memory_events: list[dict] = []


async def log_event(lead_id: str, event_type: str, detail: dict[str, Any] | None = None) -> None:
    sb = await get_supabase()
    event = EventLog(lead_id=lead_id, event_type=event_type, detail=detail or {})
    data = event.model_dump()
    if sb is None:
        _in_memory_events.append(data)
        return
    await sb.table(TABLE).insert(data).execute()


async def get_events(lead_id: str) -> list[dict]:
    sb = await get_supabase()
    if sb is None:
        events = [e for e in _in_memory_events if e.get("lead_id") == lead_id]
        events.sort(key=lambda e: e.get("created_at", ""))
        return events
        
    res = (
        await sb.table(TABLE)
        .select("*")
        .eq("lead_id", lead_id)
        .order("created_at")
        .execute()
    )
    return res.data or []
