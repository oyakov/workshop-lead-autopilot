"""Tests for follow-up service — owner reminders, auto-send, 3-step sequence."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from app.services.followup import process_followups, approve_and_send


def _make_contacted_lead(hours_ago: int = 30, followup_count: int = 0, **kw) -> dict:
    last_action = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    base = {
        "lead_id": "lead-001",
        "email": "client@company.com",
        "first_name": "Ivan",
        "last_name": "Petrov",
        "company_name": "Tech Corp",
        "inquiry_text": "Need CRM automation",
        "owner": "oleg@workshop.ai",
        "status": "contacted",
        "followup_count": followup_count,
        "last_action_at": last_action,
        "draft_subject": "Re: Inquiry",
        "draft_body": "Hi Ivan...",
        "draft_approved": False,
        "crm_contact_id": "",
    }
    base.update(kw)
    return base


@pytest.mark.asyncio
async def test_process_followups_t24_owner_reminder():
    """T+24h: owner reminder is sent when followup_count == 0."""
    lead = _make_contacted_lead(hours_ago=25, followup_count=0)
    with (
        patch("app.services.followup.leads_repo.list_leads", new_callable=AsyncMock, return_value=[lead]),
        patch("app.services.followup.leads_repo.update_lead", new_callable=AsyncMock),
        patch("app.services.followup.events_repo.log_event", new_callable=AsyncMock),
        patch("app.services.followup.alerts.send_alert", new_callable=AsyncMock) as mock_alert,
    ):
        count = await process_followups()
        assert count == 1
        mock_alert.assert_called_once()


@pytest.mark.asyncio
async def test_process_followups_t48_client_email_autosend():
    """T+48h: client follow-up email is sent automatically when FOLLOWUP_AUTO_SEND=True."""
    lead = _make_contacted_lead(hours_ago=50, followup_count=1)
    with (
        patch("app.services.followup.leads_repo.list_leads", new_callable=AsyncMock, return_value=[lead]),
        patch("app.services.followup.leads_repo.update_lead", new_callable=AsyncMock),
        patch("app.services.followup.events_repo.log_event", new_callable=AsyncMock),
        patch("app.services.followup.draft_svc.generate_followup", new_callable=AsyncMock,
              return_value=("Re: Following up", "Hi Ivan, just checking in...")),
        patch("app.services.followup.get_settings") as mock_cfg,
        patch("app.services.followup._smtp_send", new_callable=AsyncMock) as mock_smtp,
    ):
        cfg = mock_cfg.return_value
        cfg.followup_auto_send = True
        cfg.followup_client_hours = 48
        cfg.followup_final_hours = 72
        cfg.sla_hours = 24
        cfg.smtp_enabled = True

        count = await process_followups()
        assert count == 1
        mock_smtp.assert_called_once()


@pytest.mark.asyncio
async def test_process_followups_t72_final_touch():
    """T+72h: 3rd follow-up step is triggered when followup_count == 2."""
    lead = _make_contacted_lead(hours_ago=74, followup_count=2)
    with (
        patch("app.services.followup.leads_repo.list_leads", new_callable=AsyncMock, return_value=[lead]),
        patch("app.services.followup.leads_repo.update_lead", new_callable=AsyncMock),
        patch("app.services.followup.events_repo.log_event", new_callable=AsyncMock),
        patch("app.services.followup.draft_svc.generate_followup", new_callable=AsyncMock,
              return_value=("Final check-in", "Hi Ivan, last touch...")),
        patch("app.services.followup.get_settings") as mock_cfg,
        patch("app.services.followup._smtp_send", new_callable=AsyncMock) as mock_smtp,
    ):
        cfg = mock_cfg.return_value
        cfg.followup_auto_send = True
        cfg.followup_client_hours = 48
        cfg.followup_final_hours = 72
        cfg.sla_hours = 24
        cfg.smtp_enabled = True

        count = await process_followups()
        assert count == 1
        mock_smtp.assert_called_once()


@pytest.mark.asyncio
async def test_approve_and_send_success():
    """approve_and_send marks draft approved and triggers SMTP when configured."""
    lead = _make_contacted_lead()
    with (
        patch("app.services.followup.leads_repo.get_lead", new_callable=AsyncMock, return_value=lead),
        patch("app.services.followup.leads_repo.update_lead", new_callable=AsyncMock),
        patch("app.services.followup.events_repo.log_event", new_callable=AsyncMock),
        patch("app.services.followup.get_settings") as mock_cfg,
        patch("app.services.followup._smtp_send", new_callable=AsyncMock) as mock_smtp,
    ):
        cfg = mock_cfg.return_value
        cfg.smtp_enabled = True

        result = await approve_and_send("lead-001")
        assert result is True
        mock_smtp.assert_called_once_with(
            to_email="client@company.com",
            subject="Re: Inquiry",
            body="Hi Ivan...",
        )


@pytest.mark.asyncio
async def test_approve_and_send_already_approved():
    """approve_and_send returns False if draft was already approved."""
    lead = _make_contacted_lead(draft_approved=True)
    with patch("app.services.followup.leads_repo.get_lead", new_callable=AsyncMock, return_value=lead):
        result = await approve_and_send("lead-001")
        assert result is False


@pytest.mark.asyncio
async def test_approve_and_send_lead_not_found():
    """approve_and_send returns False if lead doesn't exist."""
    with patch("app.services.followup.leads_repo.get_lead", new_callable=AsyncMock, return_value=None):
        result = await approve_and_send("nonexistent")
        assert result is False
