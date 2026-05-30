"""Tests for SLA checker — verifies batch query logic and cooldown."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from app.services.sla import check_sla


@pytest.mark.asyncio
async def test_check_sla_no_overdue_leads():
    with patch("app.services.sla.leads_repo.list_leads", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = []
        result = await check_sla()
        assert result == 0


@pytest.mark.asyncio
async def test_check_sla_fires_alert_first_time():
    """Lead is overdue and has never been alerted — should alert."""
    overdue_lead = {
        "lead_id": "abc123",
        "owner": "oleg@workshop.ai",
        "status": "contacted",
        "next_action_due_at": "2000-01-01T00:00:00+00:00",
    }
    with (
        patch("app.services.sla.leads_repo.list_leads", new_callable=AsyncMock, return_value=[overdue_lead]),
        patch("app.services.sla.events_repo.get_last_event_times_by_type", new_callable=AsyncMock, return_value={}),
        patch("app.services.sla.events_repo.log_event", new_callable=AsyncMock) as mock_log,
        patch("app.services.sla.alerts.send_sla_alert", new_callable=AsyncMock) as mock_alert,
    ):
        result = await check_sla()
        assert result == 1
        mock_log.assert_called_once()
        mock_alert.assert_called_once_with(overdue_lead)


@pytest.mark.asyncio
async def test_check_sla_respects_cooldown():
    """Lead was alerted 2 hours ago — should NOT alert again (cooldown = 6h)."""
    recent_alert_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    overdue_lead = {
        "lead_id": "abc123",
        "owner": "oleg@workshop.ai",
        "status": "contacted",
        "next_action_due_at": "2000-01-01T00:00:00+00:00",
    }
    with (
        patch("app.services.sla.leads_repo.list_leads", new_callable=AsyncMock, return_value=[overdue_lead]),
        patch(
            "app.services.sla.events_repo.get_last_event_times_by_type",
            new_callable=AsyncMock,
            return_value={"abc123": recent_alert_ts},
        ),
        patch("app.services.sla.alerts.send_sla_alert", new_callable=AsyncMock) as mock_alert,
    ):
        result = await check_sla()
        assert result == 0
        mock_alert.assert_not_called()


@pytest.mark.asyncio
async def test_check_sla_alerts_after_cooldown_expires():
    """Lead was alerted 8 hours ago — cooldown expired, should alert."""
    old_alert_ts = (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat()
    overdue_lead = {
        "lead_id": "abc123",
        "owner": "oleg@workshop.ai",
        "status": "contacted",
        "next_action_due_at": "2000-01-01T00:00:00+00:00",
    }
    with (
        patch("app.services.sla.leads_repo.list_leads", new_callable=AsyncMock, return_value=[overdue_lead]),
        patch(
            "app.services.sla.events_repo.get_last_event_times_by_type",
            new_callable=AsyncMock,
            return_value={"abc123": old_alert_ts},
        ),
        patch("app.services.sla.events_repo.log_event", new_callable=AsyncMock),
        patch("app.services.sla.alerts.send_sla_alert", new_callable=AsyncMock) as mock_alert,
    ):
        result = await check_sla()
        assert result == 1
        mock_alert.assert_called_once()


@pytest.mark.asyncio
async def test_check_sla_batch_query_called_once():
    """Verifies that get_last_event_times_by_type is called exactly once (no N+1)."""
    leads = [
        {"lead_id": f"lead-{i}", "owner": "x", "status": "contacted",
         "next_action_due_at": "2000-01-01T00:00:00+00:00"}
        for i in range(10)
    ]
    with (
        patch("app.services.sla.leads_repo.list_leads", new_callable=AsyncMock, return_value=leads),
        patch(
            "app.services.sla.events_repo.get_last_event_times_by_type",
            new_callable=AsyncMock,
            return_value={},
        ) as mock_batch,
        patch("app.services.sla.events_repo.log_event", new_callable=AsyncMock),
        patch("app.services.sla.alerts.send_sla_alert", new_callable=AsyncMock),
    ):
        await check_sla()
        # Must be called exactly once regardless of number of leads
        mock_batch.assert_called_once()
