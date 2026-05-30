"""Leads repository — CRUD against Supabase `leads` table."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.db import mock_db
from app.db.client import get_supabase
from app.models.lead import Lead

TABLE = "leads"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def save_lead(lead: Lead) -> None:
    """Insert or replace a lead (upsert by lead_id)."""
    sb = await get_supabase()
    data = lead.model_dump()
    data["updated_at"] = _now_iso()
    if sb is None:
        mock_db.leads[lead.lead_id] = data
        return
    
    # For Supabase PostgreSQL, convert empty string timestamps to None
    for field in ["next_action_due_at", "followup_last_at", "last_action_at"]:
        if data.get(field) == "":
            data[field] = None
            
    await sb.table(TABLE).upsert(data).execute()


async def get_lead(lead_id: str) -> dict | None:
    sb = await get_supabase()
    if sb is None:
        return mock_db.leads.get(lead_id)
    res = await sb.table(TABLE).select("*").eq("lead_id", lead_id).maybe_single().execute()
    return res.data


async def list_leads(
    *,
    status: str | None = None,
    overdue: bool = False,
    sla_breached: bool = False,
    limit: int = 200,
) -> list[dict]:
    sb = await get_supabase()
    if sb is None:
        leads = list(mock_db.leads.values())
        leads.sort(key=lambda l: l.get("created_at", ""), reverse=True)
        if status:
            leads = [l for l in leads if l.get("status") == status]
        if overdue or sla_breached:
            now = _now_iso()
            leads = [
                l for l in leads 
                if l.get("next_action_due_at", "") < now 
                and l.get("status") in ["new", "contacted"]
            ]
        return leads[:limit]
        
    query = sb.table(TABLE).select("*").order("created_at", desc=True).limit(limit)
    if status:
        query = query.eq("status", status)
    if overdue or sla_breached:
        now = _now_iso()
        query = query.lt("next_action_due_at", now).in_("status", ["new", "contacted"])
    res = await query.execute()
    return res.data or []


async def update_lead(lead_id: str, updates: dict[str, Any]) -> None:
    sb = await get_supabase()
    updates["updated_at"] = _now_iso()
    if sb is None:
        if lead_id in mock_db.leads:
            mock_db.leads[lead_id].update(updates)
        return
        
    cleaned = dict(updates)
    for field in ["next_action_due_at", "followup_last_at", "last_action_at"]:
        if field in cleaned and cleaned[field] == "":
            cleaned[field] = None
            
    await sb.table(TABLE).update(cleaned).eq("lead_id", lead_id).execute()


async def find_by_email(email: str) -> list[dict]:
    sb = await get_supabase()
    if sb is None:
        return [
            {"lead_id": l["lead_id"], "email": l["email"], "status": l["status"], "created_at": l["created_at"]}
            for l in mock_db.leads.values() 
            if l.get("email") == email
        ]
    res = await sb.table(TABLE).select("lead_id,email,status,created_at").eq("email", email).execute()
    return res.data or []


async def find_by_domain(domain: str) -> list[dict]:
    if not domain:
        return []
    sb = await get_supabase()
    if sb is None:
        return [
            {"lead_id": l["lead_id"], "email": l["email"], "company_domain": l["company_domain"], "status": l["status"]}
            for l in mock_db.leads.values() 
            if l.get("company_domain") == domain
        ]
    res = await sb.table(TABLE).select("lead_id,email,company_domain,status").eq("company_domain", domain).execute()
    return res.data or []
