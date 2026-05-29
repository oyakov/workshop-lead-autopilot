"""Reply template model."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ReplyTemplate(BaseModel):
    template_id: str = ""
    name: str
    intent_category: str = ""   # empty = applies to all intents
    subject_tpl: str
    body_tpl: str
    is_active: bool = True
