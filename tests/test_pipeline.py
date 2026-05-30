"""Integration tests for the main lead processing pipeline."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.pipeline import process_lead


def _make_lead_input(**overrides):
    base = {
        "first_name": "Ivan",
        "last_name": "Petrov",
        "email": "ivan@techcorp.rs",
        "phone": "+381111234",
        "company_name": "Tech Corp",
        "inquiry_text": "We need to automate our CRM workflow.",
        "source": "webform",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_process_lead_happy_path():
    """Full pipeline run — verifies all steps execute and lead is saved."""
    with (
        patch("app.services.pipeline.leads_repo.save_lead", new_callable=AsyncMock),
        patch("app.services.pipeline.leads_repo.get_lead", new_callable=AsyncMock,
              return_value=_make_lead_input(lead_id="abc1", score=75, score_label="hot",
                                            intent_category="automation")),
        patch("app.services.pipeline.leads_repo.update_lead", new_callable=AsyncMock),
        patch("app.services.pipeline.events_repo.log_event", new_callable=AsyncMock),
        patch("app.services.pipeline.deduper.find_duplicate", new_callable=AsyncMock, return_value=None),
        patch("app.services.pipeline.enricher.classify_intent", new_callable=AsyncMock, return_value="automation"),
        patch("app.services.pipeline.enricher.score_lead", new_callable=AsyncMock,
              return_value=(75, "hot", "Business email + specific pain point")),
        patch("app.services.pipeline.draft.generate_draft", new_callable=AsyncMock,
              return_value=("Re: Inquiry", "Hi Ivan, ...")),
        patch("app.services.pipeline.alerts.send_new_lead_alert", new_callable=AsyncMock) as mock_alert,
        patch("app.services.pipeline.get_crm_adapter") as mock_crm_factory,
    ):
        mock_crm = MagicMock()
        mock_crm.is_configured.return_value = True
        crm_result = MagicMock(ok=True, contact_id="c1", company_id="co1", deal_id="d1")
        mock_crm.full_upsert = AsyncMock(return_value=crm_result)
        mock_crm_factory.return_value = mock_crm

        lead = await process_lead(_make_lead_input())

        assert lead.email == "ivan@techcorp.rs"
        mock_alert.assert_called_once()  # hot lead → Telegram alert fired


@pytest.mark.asyncio
async def test_process_lead_duplicate_closes_lead():
    """If dedup finds existing lead, current lead is closed_lost immediately."""
    with (
        patch("app.services.pipeline.leads_repo.save_lead", new_callable=AsyncMock),
        patch("app.services.pipeline.leads_repo.get_lead", new_callable=AsyncMock, return_value={}),
        patch("app.services.pipeline.leads_repo.update_lead", new_callable=AsyncMock) as mock_update,
        patch("app.services.pipeline.events_repo.log_event", new_callable=AsyncMock),
        patch("app.services.pipeline.deduper.find_duplicate", new_callable=AsyncMock,
              return_value={"lead_id": "existing-001"}),
        patch("app.services.pipeline.enricher.classify_intent", new_callable=AsyncMock) as mock_intent,
        patch("app.services.pipeline.draft.generate_draft", new_callable=AsyncMock) as mock_draft,
    ):
        lead = await process_lead(_make_lead_input())

        # After dedup: pipeline stops — no intent classification, no draft
        mock_intent.assert_not_called()
        mock_draft.assert_not_called()

        # Lead marked as duplicate
        update_calls = [str(c) for c in mock_update.call_args_list]
        assert any("closed_lost" in s for s in update_calls)


@pytest.mark.asyncio
async def test_process_lead_cold_skips_crm():
    """Cold leads (score < threshold) should NOT be pushed to CRM."""
    with (
        patch("app.services.pipeline.leads_repo.save_lead", new_callable=AsyncMock),
        patch("app.services.pipeline.leads_repo.get_lead", new_callable=AsyncMock,
              return_value=_make_lead_input(lead_id="cold1", score=10, score_label="cold",
                                            intent_category="other")),
        patch("app.services.pipeline.leads_repo.update_lead", new_callable=AsyncMock),
        patch("app.services.pipeline.events_repo.log_event", new_callable=AsyncMock),
        patch("app.services.pipeline.deduper.find_duplicate", new_callable=AsyncMock, return_value=None),
        patch("app.services.pipeline.enricher.classify_intent", new_callable=AsyncMock, return_value="other"),
        patch("app.services.pipeline.enricher.score_lead", new_callable=AsyncMock,
              return_value=(10, "cold", "Spam-like inquiry")),
        patch("app.services.pipeline.draft.generate_draft", new_callable=AsyncMock,
              return_value=("Subject", "Body")),
        patch("app.services.pipeline.alerts.send_new_lead_alert", new_callable=AsyncMock) as mock_alert,
        patch("app.services.pipeline.get_crm_adapter") as mock_crm_factory,
    ):
        mock_crm = MagicMock()
        mock_crm.is_configured.return_value = True
        mock_crm.full_upsert = AsyncMock()
        mock_crm_factory.return_value = mock_crm

        await process_lead(_make_lead_input())

        # CRM should NOT be called for cold lead
        mock_crm.full_upsert.assert_not_called()
        # No Telegram alert for cold lead
        mock_alert.assert_not_called()


@pytest.mark.asyncio
async def test_process_lead_crm_failure_does_not_abort():
    """CRM failure should be logged but not abort the pipeline."""
    with (
        patch("app.services.pipeline.leads_repo.save_lead", new_callable=AsyncMock),
        patch("app.services.pipeline.leads_repo.get_lead", new_callable=AsyncMock,
              return_value=_make_lead_input(lead_id="h1", score=80, score_label="hot",
                                            intent_category="automation")),
        patch("app.services.pipeline.leads_repo.update_lead", new_callable=AsyncMock),
        patch("app.services.pipeline.events_repo.log_event", new_callable=AsyncMock),
        patch("app.services.pipeline.deduper.find_duplicate", new_callable=AsyncMock, return_value=None),
        patch("app.services.pipeline.enricher.classify_intent", new_callable=AsyncMock, return_value="automation"),
        patch("app.services.pipeline.enricher.score_lead", new_callable=AsyncMock,
              return_value=(80, "hot", "Hot lead")),
        patch("app.services.pipeline.draft.generate_draft", new_callable=AsyncMock,
              return_value=("Subject", "Body")) as mock_draft,
        patch("app.services.pipeline.alerts.send_new_lead_alert", new_callable=AsyncMock),
        patch("app.services.pipeline.get_crm_adapter") as mock_crm_factory,
    ):
        mock_crm = MagicMock()
        mock_crm.is_configured.return_value = True
        mock_crm.full_upsert = AsyncMock(side_effect=Exception("HubSpot is down"))
        mock_crm_factory.return_value = mock_crm

        lead = await process_lead(_make_lead_input())

        # Pipeline continued despite CRM failure — draft was still generated
        assert lead is not None
        mock_draft.assert_called_once()
