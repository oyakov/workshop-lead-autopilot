from datetime import datetime, timedelta
from models import Lead, EventLog
from services import db, normalizer, enricher, draft
from services import hubspot as hs


async def process_lead(raw: dict) -> Lead:
    # Normalize
    normalized = normalizer.normalize_lead(raw)
    lead = Lead(**normalized)
    lead.owner = normalizer.assign_owner()
    lead.next_action_due_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()

    await db.save_lead(lead.model_dump())
    await _log(lead.lead_id, "lead_received", f"source={lead.source}")
    await _log(lead.lead_id, "lead_normalized", f"domain={lead.company_domain}")

    # Dedup check
    existing = await db.list_leads()
    dupes = [l for l in existing if l["email"] == lead.email and l["lead_id"] != lead.lead_id]
    if dupes:
        await _log(lead.lead_id, "lead_deduped", f"duplicate_of={dupes[0]['lead_id']}")
        await db.update_lead(lead.lead_id, {"status": "closed_lost", "draft_body": "DUPLICATE"})
        return lead

    # Classify intent
    intent = await enricher.classify_intent(lead.inquiry_text)
    await db.update_lead(lead.lead_id, {"intent_category": intent})
    await _log(lead.lead_id, "lead_enriched", f"intent={intent}")

    # Push to HubSpot CRM (if configured)
    lead_data = await db.get_lead(lead.lead_id)
    if hs.is_configured():
        try:
            deal_id = await hs.create_deal(lead_data)
            await db.update_lead(lead.lead_id, {"crm_deal_id": deal_id})
            await _log(lead.lead_id, "crm_upsert_success", f"hubspot_deal={deal_id}")
        except Exception as e:
            await _log(lead.lead_id, "crm_upsert_failed", str(e)[:120])

    # Generate draft reply
    lead_data = await db.get_lead(lead.lead_id)
    subject, body = await draft.generate_draft(lead_data)
    await db.update_lead(lead.lead_id, {
        "draft_subject": subject,
        "draft_body": body,
        "status": "contacted"
    })
    await _log(lead.lead_id, "draft_generated", f"subject={subject[:60]}")
    await _log(lead.lead_id, "human_approval_requested", "awaiting manager approval")

    return lead


async def approve_draft(lead_id: str) -> bool:
    lead = await db.get_lead(lead_id)
    if not lead or lead.get("draft_approved"):
        return False
    await db.update_lead(lead_id, {
        "draft_approved": True,
        "status": "contacted",
        "last_action_at": datetime.utcnow().isoformat()
    })
    await _log(lead_id, "human_approval_approved", "draft approved by manager")
    await _log(lead_id, "email_sent_simulated", f"to={lead['email']}")
    return True


async def check_stale_leads():
    """Called by scheduler — alerts on leads past SLA."""
    leads = await db.list_leads()
    now = datetime.utcnow()
    for lead in leads:
        if lead["status"] not in ("new", "contacted"):
            continue
        due = lead.get("next_action_due_at", "")
        if not due:
            continue
        try:
            due_dt = datetime.fromisoformat(due)
        except ValueError:
            continue
        if now > due_dt:
            await _log(lead["lead_id"], "alert_sla_breached", f"owner={lead['owner']}")


async def _log(lead_id: str, event_type: str, detail: str = ""):
    event = EventLog(lead_id=lead_id, event_type=event_type, detail=detail)
    await db.log_event(event.model_dump())
