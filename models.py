from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
import uuid

LeadStatus = Literal["new", "contacted", "qualified", "meeting_set", "closed_won", "closed_lost"]
IntentCategory = Literal["automation", "integration", "pricing", "partnership", "other"]


class LeadIn(BaseModel):
    first_name: str
    last_name: str = ""
    email: str
    phone: str = ""
    company_name: str = ""
    inquiry_text: str
    source: str = "webform"


class Lead(BaseModel):
    lead_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str = "webform"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    first_name: str
    last_name: str = ""
    email: str
    phone: str = ""
    company_name: str = ""
    company_domain: str = ""
    inquiry_text: str
    intent_category: IntentCategory = "other"
    owner: str = "unassigned"
    status: LeadStatus = "new"
    crm_deal_id: str = ""
    last_action_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    next_action_due_at: str = ""
    draft_subject: str = ""
    draft_body: str = ""
    draft_approved: bool = False


class EventLog(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    lead_id: str
    event_type: str
    detail: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
