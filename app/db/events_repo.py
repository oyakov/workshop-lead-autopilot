"""Events repository — append-only audit log."""
from __future__ import annotations

from typing import Any

from app.db.client import get_supabase
from app.models.event import EventLog

TABLE = "events"


async def log_event(lead_id: str, event_type: str, detail: dict[str, Any] | None = None) -> None:
    sb = await get_supabase()
    event = EventLog(lead_id=lead_id, event_type=event_type, detail=detail or {})
    await sb.table(TABLE).insert(event.model_dump()).execute()


async def get_events(lead_id: str) -> list[dict]:
    sb = await get_supabase()
    res = (
        await sb.table(TABLE)
        .select("*")
        .eq("lead_id", lead_id)
        .order("created_at")
        .execute()
    )
    return res.data or []
