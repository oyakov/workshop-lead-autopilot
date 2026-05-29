"""Lead domain models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Type aliases ──────────────────────────────────────────────────────────────
LeadStatus = Literal[
    "new", "contacted", "qualified", "meeting_set", "closed_won", "closed_lost"
]
IntentCategory = Literal[
    "automation", "integration", "pricing", "partnership", "other"
]
ScoreLabel = Literal["hot", "warm", "cold", "unknown"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_uuid() -> str:
    return str(uuid.uuid4())[:8]


# ── API input model ───────────────────────────────────────────────────────────
class LeadIn(BaseModel):
    """Inbound lead payload from web form / webhook."""
    first_name: str
    last_name: str = ""
    email: str
    phone: str = ""
    company_name: str = ""
    inquiry_text: str
    source: str = "webform"
    country: str = ""
    timezone: str = ""


# ── Core domain model ─────────────────────────────────────────────────────────
class Lead(BaseModel):
    lead_id: str = Field(default_factory=_short_uuid)
    source: str = "webform"
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)

    # Contact info
    first_name: str
    last_name: str = ""
    email: str
    phone: str = ""

    # Company info
    company_name: str = ""
    company_domain: str = ""
    country: str = ""
    timezone: str = ""

    # Lead details
    inquiry_text: str
    intent_category: IntentCategory = "other"

    # Scoring (v1)
    score: int = 0                         # 0–100
    score_label: ScoreLabel = "unknown"    # hot / warm / cold
    score_reason: str = ""                 # LLM explanation

    # Ownership & workflow
    owner: str = "unassigned"
    status: LeadStatus = "new"

    # CRM references
    crm_contact_id: str = ""
    crm_company_id: str = ""
    crm_deal_id: str = ""

    # Timeline
    last_action_at: str = Field(default_factory=_now_iso)
    next_action_due_at: str = ""

    # Draft email
    draft_subject: str = ""
    draft_body: str = ""
    draft_approved: bool = False
    draft_sent: bool = False

    # Follow-up tracking
    followup_count: int = 0
    followup_last_at: str = ""
