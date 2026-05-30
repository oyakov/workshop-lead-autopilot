"""Events repository — append-only audit log."""
from __future__ import annotations

from typing import Any

from app.db import mock_db
from app.db.client import get_supabase
from app.models.event import EventLog

TABLE = "events"


async def log_event(lead_id: str, event_type: str, detail: dict[str, Any] | None = None) -> None:
    sb = await get_supabase()
    event = EventLog(lead_id=lead_id, event_type=event_type, detail=detail or {})
    data = event.model_dump()
    if sb is None:
        mock_db.events.append(data)
        return
    await sb.table(TABLE).insert(data).execute()


async def get_events(lead_id: str) -> list[dict]:
    sb = await get_supabase()
    if sb is None:
        events = [e for e in mock_db.events if e.get("lead_id") == lead_id]
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


async def get_last_event_times_by_type(
    lead_ids: list[str],
    event_type: str,
) -> dict[str, str]:
    """
    Batch query: returns {lead_id: last_created_at} for the given event_type.
    Single DB round-trip instead of N per lead — fixes the SLA N+1 problem.
    """
    if not lead_ids:
        return {}

    sb = await get_supabase()
    if sb is None:
        result: dict[str, str] = {}
        for e in mock_db.events:
            if e.get("event_type") == event_type and e.get("lead_id") in lead_ids:
                lid = e["lead_id"]
                ts = e.get("created_at", "")
                if lid not in result or ts > result[lid]:
                    result[lid] = ts
        return result

    res = (
        await sb.table(TABLE)
        .select("lead_id,created_at")
        .in_("lead_id", lead_ids)
        .eq("event_type", event_type)
        .order("created_at", desc=True)
        .execute()
    )
    result = {}
    for row in res.data or []:
        lid = row["lead_id"]
        ts = row["created_at"]
        if lid not in result:  # already sorted desc, first hit = latest
            result[lid] = ts
    return result
