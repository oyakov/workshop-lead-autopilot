"""SLA checker — finds overdue leads and fires alerts."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.db import leads_repo, events_repo
from app.services import alerts
from app.services.utils import parse_iso_datetime

logger = logging.getLogger(__name__)


async def check_sla() -> int:
    """
    Find leads past their next_action_due_at and:
    1. Log alert_sla_breached event
    2. Send Telegram alert
    
    Returns count of breached leads.
    """
    overdue = await leads_repo.list_leads(sla_breached=True)
    count = 0
    for lead in overdue:
        lead_id = lead["lead_id"]
        # Avoid duplicate alerts: check if already alerted in last 6h
        events = await events_repo.get_events(lead_id)
        recent_alerts = [
            e for e in events
            if e["event_type"] == "alert_sla_breached"
        ]
        if recent_alerts:
            last_alert_iso = recent_alerts[-1]["created_at"]
            last_alert_dt = parse_iso_datetime(last_alert_iso)
            hours_since = (datetime.now(timezone.utc) - last_alert_dt).total_seconds() / 3600
            if hours_since < 6:
                continue  # Already alerted recently

        await events_repo.log_event(lead_id, "alert_sla_breached", {
            "owner": lead.get("owner"),
            "status": lead.get("status"),
            "next_action_due_at": lead.get("next_action_due_at"),
        })
        await alerts.send_sla_alert(lead)
        count += 1
        logger.warning("SLA breach: lead=%s owner=%s", lead_id, lead.get("owner"))

    return count
