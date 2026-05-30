"""SLA checker — finds overdue leads and fires alerts.

Fix: replaced N+1 per-lead event queries with a single batch query
via events_repo.get_last_event_times_by_type().
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.db import leads_repo, events_repo
from app.services import alerts
from app.services.utils import parse_iso_datetime

logger = logging.getLogger(__name__)

_SLA_COOLDOWN_HOURS = 6


async def check_sla() -> int:
    """
    Find leads past their next_action_due_at and:
    1. Log alert_sla_breached event
    2. Send Telegram alert

    Returns count of breached leads.
    Uses a single batch query for recent alert times — no N+1.
    """
    overdue = await leads_repo.list_leads(sla_breached=True)
    if not overdue:
        return 0

    lead_ids = [l["lead_id"] for l in overdue]

    # Single batch query: last alert time per lead — O(1) round-trips
    last_alerts: dict[str, str] = await events_repo.get_last_event_times_by_type(
        lead_ids, "alert_sla_breached"
    )

    now = datetime.now(timezone.utc)
    count = 0

    for lead in overdue:
        lead_id = lead["lead_id"]

        last_alert_iso = last_alerts.get(lead_id)
        if last_alert_iso:
            try:
                last_alert_dt = parse_iso_datetime(last_alert_iso)
                hours_since = (now - last_alert_dt).total_seconds() / 3600
                if hours_since < _SLA_COOLDOWN_HOURS:
                    continue  # Already alerted within cooldown window
            except Exception:
                pass

        await events_repo.log_event(lead_id, "alert_sla_breached", {
            "owner": lead.get("owner"),
            "status": lead.get("status"),
            "next_action_due_at": lead.get("next_action_due_at"),
        })
        await alerts.send_sla_alert(lead)
        count += 1
        logger.warning("SLA breach: lead=%s owner=%s", lead_id, lead.get("owner"))

    return count
