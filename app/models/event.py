"""Event log model — append-only audit trail per lead."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventLog(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    lead_id: str
    event_type: str
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_now_iso)
