"""Draft reply generator — LLM-powered with template fallback."""
from __future__ import annotations

import logging
import os
import re

from app.config import get_settings
from app.llm import gateway as llm
from app.llm.prompts import DRAFT_REPLY, FOLLOWUP_EMAIL

logger = logging.getLogger(__name__)


async def generate_draft(lead: dict) -> tuple[str, str]:
    """
    Generate first-reply draft email.
    Returns (subject, body).
    Falls back to a static template if LLM fails.
    """
    cfg = get_settings()
    agency = cfg.agency_name

    fallback_subject = f"Re: Your inquiry — {lead.get('first_name', 'there')}"
    fallback_body = (
        f"Hi {lead.get('first_name', 'there')},\n\n"
        f"Thanks for reaching out! We specialise in automating exactly "
        f"the kind of workflows you described.\n"
        f"Would you be open to a quick 15-min call this week?\n\n"
        f"Best,\nThe {agency} Team"
    )

    try:
        prompt = DRAFT_REPLY.format(
            agency_name=agency,
            first_name=lead.get("first_name", ""),
            last_name=lead.get("last_name", ""),
            company_name=lead.get("company_name", "their company"),
            inquiry_text=lead.get("inquiry_text", "")[:400],
            intent_category=lead.get("intent_category", "other"),
            score_label=lead.get("score_label", "unknown"),
        )
        text = await llm.chat(
            [{"role": "user", "content": prompt}],
            max_tokens=400,
        )

        if not text:
            return fallback_subject, fallback_body

        return _parse_draft(text, fallback_subject, fallback_body)

    except Exception as e:
        logger.warning("Draft generation failed: %s", e)
        return fallback_subject, fallback_body


async def generate_followup(lead: dict) -> tuple[str, str]:
    """
    Generate follow-up email.
    Returns (subject, body).
    """
    from datetime import datetime, timezone
    cfg = get_settings()
    agency = cfg.agency_name

    try:
        last_action = lead.get("last_action_at", "")
        if last_action:
            last_dt = datetime.fromisoformat(last_action.replace("Z", "+00:00"))
            days = (datetime.now(timezone.utc) - last_dt).days
        else:
            days = 1

        prompt = FOLLOWUP_EMAIL.format(
            agency_name=agency,
            first_name=lead.get("first_name", "there"),
            company_name=lead.get("company_name", ""),
            inquiry_text=lead.get("inquiry_text", "")[:300],
            days_since_contact=days,
            followup_count=lead.get("followup_count", 1),
        )
        text = await llm.chat(
            [{"role": "user", "content": prompt}],
            max_tokens=300,
        )
        fallback_subject = f"Following up — {agency}"
        fallback_body = (
            f"Hi {lead.get('first_name','there')},\n\n"
            f"Just checking in on our previous message. Happy to answer "
            f"any questions or find a time for a quick call.\n\n"
            f"Best,\nThe {agency} Team"
        )
        if not text:
            return fallback_subject, fallback_body
        return _parse_draft(text, fallback_subject, fallback_body)

    except Exception as e:
        logger.warning("Follow-up draft generation failed: %s", e)
        fallback_subject = f"Following up — {cfg.agency_name}"
        fallback_body = f"Hi {lead.get('first_name','there')}, just checking in. Best, The {cfg.agency_name} Team"
        return fallback_subject, fallback_body


def _parse_draft(text: str, fallback_subject: str, fallback_body: str) -> tuple[str, str]:
    lines = text.strip().splitlines()
    subject = fallback_subject
    body_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.lower().startswith("subject:"):
            subject = stripped.split(":", 1)[1].strip()
            body_start = i + 1
            break

    body = "\n".join(lines[body_start:]).strip()
    # Clean placeholder artifacts
    body = re.sub(r"\[Your Name\]", get_settings().agency_name, body)
    body = re.sub(r"\[.*?\]", "", body).strip()

    return subject, body or fallback_body
