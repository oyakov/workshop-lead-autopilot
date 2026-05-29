"""
Lead processing pipeline — main orchestrator.

Flow:
  1. Normalize fields
  2. Check deduplication
  3. Classify intent (LLM)
  4. Score lead (LLM + rules)
  5. Assign owner (routing)
  6. Push to CRM
  7. Generate draft reply (LLM)
  8. Telegram alert for hot leads
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.crm.factory import get_crm_adapter
from app.db import events_repo, leads_repo
from app.models.lead import Lead
from app.services import alerts, deduper, draft, enricher, normalizer, routing

logger = logging.getLogger(__name__)


async def process_lead(raw: dict) -> Lead:
    """
    Full pipeline: intake → enrich → CRM → draft.
    Always persists the lead even on partial failures.
    """
    cfg = get_settings()

    # ── 1. Normalize ──────────────────────────────────────────
    normalized = normalizer.normalize_lead(raw)
    lead = Lead(**normalized)
    lead.owner = routing.get_owner()
    lead.next_action_due_at = (
        datetime.now(timezone.utc) + timedelta(hours=cfg.sla_hours)
    ).isoformat()

    await leads_repo.save_lead(lead)
    await _log(lead.lead_id, "lead_received", {"source": lead.source})
    await _log(lead.lead_id, "lead_normalized", {"domain": lead.company_domain, "owner": lead.owner})

    # ── 2. Deduplication ──────────────────────────────────────
    dupe = await deduper.find_duplicate(lead.email, lead.company_domain, lead.lead_id)
    if dupe:
        await leads_repo.update_lead(lead.lead_id, {
            "status": "closed_lost",
            "draft_body": f"DUPLICATE of {dupe['lead_id']}",
        })
        await _log(lead.lead_id, "lead_deduped", {"duplicate_of": dupe["lead_id"]})
        return lead

    # ── 3. Intent classification ──────────────────────────────
    intent = await enricher.classify_intent(lead.inquiry_text)
    await leads_repo.update_lead(lead.lead_id, {"intent_category": intent})
    await _log(lead.lead_id, "lead_intent_classified", {"intent": intent})

    # Refresh lead data for scoring
    lead_data = await leads_repo.get_lead(lead.lead_id) or lead.model_dump()

    # ── 4. Score lead ─────────────────────────────────────────
    if cfg.scoring_enabled:
        score, score_label, score_reason = await enricher.score_lead(lead_data)
        await leads_repo.update_lead(lead.lead_id, {
            "score": score,
            "score_label": score_label,
            "score_reason": score_reason,
        })
        await _log(lead.lead_id, "lead_scored", {
            "score": score,
            "label": score_label,
            "reason": score_reason[:120],
        })
        lead_data = await leads_repo.get_lead(lead.lead_id) or lead_data

    # ── 5. CRM upsert ─────────────────────────────────────────
    crm = get_crm_adapter()
    if crm.is_configured():
        try:
            result = await crm.full_upsert(lead_data)
            if result.ok:
                await leads_repo.update_lead(lead.lead_id, {
                    "crm_contact_id": result.contact_id,
                    "crm_company_id": result.company_id,
                    "crm_deal_id": result.deal_id,
                })
                await _log(lead.lead_id, "crm_upsert_success", {
                    "provider": cfg.crm_provider,
                    "deal_id": result.deal_id,
                    "contact_id": result.contact_id,
                })
            else:
                await _log(lead.lead_id, "crm_upsert_failed", {"error": result.error})
        except Exception as e:
            await _log(lead.lead_id, "crm_upsert_failed", {"error": str(e)[:200]})
            logger.error("CRM upsert failed for lead=%s: %s", lead.lead_id, e)

    # Refresh again post-CRM
    lead_data = await leads_repo.get_lead(lead.lead_id) or lead_data

    # ── 6. Generate draft ─────────────────────────────────────
    subject, body = await draft.generate_draft(lead_data)
    await leads_repo.update_lead(lead.lead_id, {
        "draft_subject": subject,
        "draft_body": body,
        "status": "contacted",
        "last_action_at": datetime.now(timezone.utc).isoformat(),
    })
    await _log(lead.lead_id, "draft_generated", {"subject": subject[:80]})
    await _log(lead.lead_id, "human_approval_requested", {
        "auto_send": cfg.followup_auto_send,
    })

    # ── 7. Telegram alert for hot leads ───────────────────────
    final_lead = await leads_repo.get_lead(lead.lead_id) or lead_data
    score_label = final_lead.get("score_label", "unknown")
    if score_label in ("hot", "warm"):
        await alerts.send_new_lead_alert(final_lead)

    return lead


async def _log(lead_id: str, event_type: str, detail: dict | None = None) -> None:
    try:
        await events_repo.log_event(lead_id, event_type, detail or {})
    except Exception as e:
        logger.error("Event log failed [%s/%s]: %s", lead_id, event_type, e)
