"""Leads repository — CRUD against Supabase `leads` table."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.db.client import get_supabase
from app.models.lead import Lead

TABLE = "leads"

# Local in-memory store for fallback execution (e.g. testing or local desktop run without Supabase credentials)
_in_memory_leads: dict[str, dict] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def save_lead(lead: Lead) -> None:
    """Insert or replace a lead (upsert by lead_id)."""
    sb = await get_supabase()
    data = lead.model_dump()
    data["updated_at"] = _now_iso()
    if sb is None:
        _in_memory_leads[lead.lead_id] = data
        return
    await sb.table(TABLE).upsert(data).execute()


async def get_lead(lead_id: str) -> dict | None:
    sb = await get_supabase()
    if sb is None:
        return _in_memory_leads.get(lead_id)
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
        leads = list(_in_memory_leads.values())
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
        if lead_id in _in_memory_leads:
            _in_memory_leads[lead_id].update(updates)
        return
    await sb.table(TABLE).update(updates).eq("lead_id", lead_id).execute()


async def find_by_email(email: str) -> list[dict]:
    sb = await get_supabase()
    if sb is None:
        return [
            {"lead_id": l["lead_id"], "email": l["email"], "status": l["status"], "created_at": l["created_at"]}
            for l in _in_memory_leads.values() 
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
            for l in _in_memory_leads.values() 
            if l.get("company_domain") == domain
        ]
    res = await sb.table(TABLE).select("lead_id,email,company_domain,status").eq("company_domain", domain).execute()
    return res.data or []
