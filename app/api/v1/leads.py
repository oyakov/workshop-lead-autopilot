"""Leads API — CRUD + pipeline actions."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.db import events_repo, leads_repo
from app.models.lead import LeadIn
from app.services import followup as followup_svc
from app.services.pipeline import process_lead
from app.services.sla import check_sla

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", status_code=202)
async def intake_lead(lead_in: LeadIn):
    """Submit a new lead for processing."""
    lead = await process_lead(lead_in.model_dump())
    return {
        "lead_id": lead.lead_id,
        "status": "processing",
        "owner": lead.owner,
    }


@router.get("")
async def list_leads(
    status: str | None = Query(None),
    overdue: bool = Query(False),
    sla_breached: bool = Query(False),
    limit: int = Query(200, ge=1, le=1000),
):
    """List leads with optional filters."""
    return await leads_repo.list_leads(
        status=status,
        overdue=overdue,
        sla_breached=sla_breached,
        limit=limit,
    )


@router.get("/{lead_id}")
async def get_lead(lead_id: str):
    lead = await leads_repo.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id!r} not found")
    return lead


@router.get("/{lead_id}/events")
async def get_lead_events(lead_id: str):
    """Get full event log for a lead."""
    return await events_repo.get_events(lead_id)


@router.post("/{lead_id}/approve")
async def approve_lead_draft(lead_id: str):
    """Approve the generated draft and send it."""
    ok = await followup_svc.approve_and_send(lead_id)
    if not ok:
        raise HTTPException(400, "Cannot approve: lead not found or already approved")
    return {"ok": True, "lead_id": lead_id}


@router.post("/{lead_id}/followup")
async def trigger_followup(lead_id: str):
    """Manually trigger follow-up processing for a single lead."""
    lead = await leads_repo.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, f"Lead {lead_id!r} not found")
    # Force-process by temporarily resetting followup_count handled externally
    count = await followup_svc.process_followups()
    return {"ok": True, "processed": count}


@router.post("/{lead_id}/sla-check")
async def manual_sla_check(lead_id: str):
    """Demo/test: manually trigger SLA breach check."""
    from datetime import datetime, timezone
    await leads_repo.update_lead(lead_id, {
        "next_action_due_at": "2000-01-01T00:00:00+00:00"
    })
    breached = await check_sla()
    return {"ok": True, "breached_count": breached}


@router.patch("/{lead_id}/status")
async def update_status(lead_id: str, status: str):
    """Update lead status."""
    from app.models.lead import LeadStatus
    valid = {"new", "contacted", "qualified", "meeting_set", "closed_won", "closed_lost"}
    if status not in valid:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid}")
    await leads_repo.update_lead(lead_id, {"status": status})
    return {"ok": True, "lead_id": lead_id, "status": status}
