"""
Webhook endpoints for n8n and external integrations.
n8n calls these to trigger actions after its own workflow steps.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.db import leads_repo, events_repo
from app.services import alerts

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/n8n/followup-trigger")
async def n8n_followup_trigger():
    """Called by n8n Follow-up Scheduler workflow."""
    from app.services.followup import process_followups
    count = await process_followups()
    return {"ok": True, "processed": count}


@router.post("/n8n/sla-check")
async def n8n_sla_check():
    """Called by n8n SLA Monitor workflow."""
    from app.services.sla import check_sla
    breached = await check_sla()
    return {"ok": True, "breached": breached}


@router.post("/n8n/email-approved")
async def n8n_email_approved(payload: dict):
    """Called by n8n when email approval is confirmed via Telegram bot."""
    lead_id = payload.get("lead_id")
    if not lead_id:
        raise HTTPException(400, "lead_id required")
    from app.services.followup import approve_and_send
    ok = await approve_and_send(lead_id)
    return {"ok": ok, "lead_id": lead_id}


@router.post("/intake")
async def generic_webhook_intake(request: Request):
    """
    Generic webhook intake — accepts any JSON payload.
    Maps common field names to LeadIn schema.
    Useful for Tally, Typeform, Webflow, etc.
    """
    body = await request.json()

    # Field name normalisation for common form builders
    field_map = {
        "name": "first_name",
        "full_name": "first_name",
        "email_address": "email",
        "message": "inquiry_text",
        "question": "inquiry_text",
        "company": "company_name",
        "organisation": "company_name",
        "organization": "company_name",
        "telephone": "phone",
        "mobile": "phone",
    }
    normalized: dict = {}
    for k, v in body.items():
        key = field_map.get(k.lower(), k.lower())
        normalized[key] = v

    # Split full name if first_name looks like a full name
    if " " in normalized.get("first_name", "") and not normalized.get("last_name"):
        parts = normalized["first_name"].split(maxsplit=1)
        normalized["first_name"] = parts[0]
        normalized["last_name"] = parts[1]

    from app.models.lead import LeadIn
    from app.services.pipeline import process_lead
    try:
        lead_in = LeadIn(**normalized)
    except Exception as e:
        raise HTTPException(422, f"Invalid payload: {e}")

    lead = await process_lead(lead_in.model_dump())
    return {"lead_id": lead.lead_id, "status": "processing"}
