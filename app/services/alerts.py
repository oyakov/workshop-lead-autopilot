"""Telegram alert service."""
from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


async def send_alert(message: str) -> None:
    """Send an alert message to all configured Telegram chat IDs."""
    cfg = get_settings()
    if not cfg.telegram_enabled or not cfg.telegram_bot_token:
        return

    chat_ids = cfg.telegram_chat_id_list
    if not chat_ids:
        return

    try:
        import httpx
        url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            for chat_id in chat_ids:
                await client.post(url, json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                })
    except Exception as e:
        logger.error("Telegram alert failed: %s", e)


async def send_sla_alert(lead: dict) -> None:
    owner = lead.get("owner", "unassigned")
    name = f"{lead.get('first_name','')} {lead.get('last_name','')}".strip() or "Unknown"
    company = lead.get("company_name", "")
    lead_id = lead.get("lead_id", "?")
    status = lead.get("status", "?")
    due = lead.get("next_action_due_at", "")

    msg = (
        f"🔴 <b>SLA Breach</b>\n"
        f"Lead: <b>{name}</b> ({company})\n"
        f"Owner: {owner}\n"
        f"Status: {status}\n"
        f"Due: {due}\n"
        f"ID: <code>{lead_id}</code>"
    )
    await send_alert(msg)


async def send_new_lead_alert(lead: dict) -> None:
    name = f"{lead.get('first_name','')} {lead.get('last_name','')}".strip()
    company = lead.get("company_name", "")
    score_label = lead.get("score_label", "unknown")
    score = lead.get("score", 0)
    intent = lead.get("intent_category", "other")
    owner = lead.get("owner", "unassigned")
    lead_id = lead.get("lead_id", "?")

    emoji = {"hot": "🔥", "warm": "🟡", "cold": "🧊"}.get(score_label, "📩")
    msg = (
        f"{emoji} <b>New Lead</b> [{score_label.upper()} {score}/100]\n"
        f"Name: <b>{name}</b> ({company})\n"
        f"Intent: {intent}\n"
        f"Owner: {owner}\n"
        f"ID: <code>{lead_id}</code>"
    )
    await send_alert(msg)
