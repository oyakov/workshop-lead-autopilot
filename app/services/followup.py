"""
Follow-up service.
- Configurable auto-send (FOLLOWUP_AUTO_SEND)
- T+24h: reminder to owner via Telegram
- T+48h: follow-up email to client (auto or human approval)
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings
from app.db import leads_repo, events_repo
from app.services import alerts, draft as draft_svc

logger = logging.getLogger(__name__)


async def process_followups() -> int:
    """
    Called by APScheduler. Processes all leads needing follow-up action.
    Returns number of actions taken.
    """
    cfg = get_settings()
    now = datetime.now(timezone.utc)
    actions = 0

    leads = await leads_repo.list_leads(status="contacted")
    for lead in leads:
        last_action_iso = lead.get("last_action_at") or lead.get("created_at", "")
        if not last_action_iso:
            continue
        try:
            last_dt = datetime.fromisoformat(last_action_iso.replace("Z", "+00:00"))
        except ValueError:
            continue

        hours_since = (now - last_dt).total_seconds() / 3600
        followup_count = lead.get("followup_count", 0)

        # T+24h: reminder to owner (always)
        if hours_since >= cfg.sla_hours and followup_count == 0:
            await _remind_owner(lead)
            actions += 1

        # T+48h: follow-up email to client
        elif hours_since >= cfg.followup_client_hours and followup_count == 1:
            if cfg.followup_auto_send:
                await _send_followup_email(lead)
            else:
                await _request_followup_approval(lead)
            actions += 1

    return actions


async def _remind_owner(lead: dict) -> None:
    lead_id = lead["lead_id"]
    owner = lead.get("owner", "unassigned")
    name = f"{lead.get('first_name','')} {lead.get('last_name','')}".strip()

    await events_repo.log_event(lead_id, "followup_reminder_sent", {"owner": owner})
    await leads_repo.update_lead(lead_id, {
        "followup_count": 1,
        "followup_last_at": datetime.now(timezone.utc).isoformat(),
    })

    msg = (
        f"⏰ <b>Follow-up Reminder</b>\n"
        f"Lead <b>{name}</b> hasn't moved in 24h.\n"
        f"Owner: {owner}\n"
        f"ID: <code>{lead_id}</code>\n"
        f"Please take action or send the draft reply."
    )
    await alerts.send_alert(msg)
    logger.info("Owner reminder sent for lead=%s", lead_id)


async def _send_followup_email(lead: dict) -> None:
    lead_id = lead["lead_id"]
    subject, body = await draft_svc.generate_followup(lead)

    await leads_repo.update_lead(lead_id, {
        "followup_count": (lead.get("followup_count", 1) + 1),
        "followup_last_at": datetime.now(timezone.utc).isoformat(),
        "last_action_at": datetime.now(timezone.utc).isoformat(),
    })

    cfg = get_settings()
    if cfg.smtp_enabled:
        try:
            await _smtp_send(
                to_email=lead.get("email", ""),
                subject=subject,
                body=body,
            )
            await events_repo.log_event(lead_id, "followup_email_sent", {
                "subject": subject[:80],
                "auto": True,
            })
            logger.info("Follow-up email sent auto to lead=%s", lead_id)
        except Exception as e:
            await events_repo.log_event(lead_id, "followup_email_failed", {"error": str(e)[:120]})
            logger.error("Follow-up email failed for lead=%s: %s", lead_id, e)
    else:
        await events_repo.log_event(lead_id, "followup_simulated", {
            "subject": subject[:80],
            "note": "SMTP disabled — email not sent",
        })


async def _request_followup_approval(lead: dict) -> None:
    lead_id = lead["lead_id"]
    subject, body = await draft_svc.generate_followup(lead)

    await leads_repo.update_lead(lead_id, {
        "draft_subject": subject,
        "draft_body": body,
        "draft_approved": False,
    })
    await events_repo.log_event(lead_id, "followup_approval_requested", {"subject": subject[:80]})

    msg = (
        f"📋 <b>Follow-up Approval Needed</b>\n"
        f"Lead: {lead.get('first_name','')} {lead.get('last_name','')}\n"
        f"Subject: {subject}\n"
        f"Approve via dashboard: /leads/{lead_id}/approve"
    )
    await alerts.send_alert(msg)


async def approve_and_send(lead_id: str) -> bool:
    """Approve and send the draft reply (first email or follow-up)."""
    lead = await leads_repo.get_lead(lead_id)
    if not lead:
        return False
    if lead.get("draft_approved"):
        return False

    await leads_repo.update_lead(lead_id, {
        "draft_approved": True,
        "draft_sent": True,
        "status": "contacted",
        "last_action_at": datetime.now(timezone.utc).isoformat(),
    })
    await events_repo.log_event(lead_id, "draft_approved_and_sent", {
        "subject": lead.get("draft_subject", "")[:80],
    })

    cfg = get_settings()
    if cfg.smtp_enabled:
        try:
            await _smtp_send(
                to_email=lead.get("email", ""),
                subject=lead.get("draft_subject", ""),
                body=lead.get("draft_body", ""),
            )
        except Exception as e:
            logger.error("SMTP send failed after approval: %s", e)

    return True


async def _smtp_send(to_email: str, subject: str, body: str) -> None:
    cfg = get_settings()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.smtp_from or cfg.smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as server:
        server.starttls(context=context)
        server.login(cfg.smtp_user, cfg.smtp_password)
        server.sendmail(cfg.smtp_from or cfg.smtp_user, to_email, msg.as_string())
