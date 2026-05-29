from __future__ import annotations

import pytest
from app.services.pipeline import process_lead
from app.models.lead import Lead


@pytest.mark.asyncio
async def test_process_lead_pipeline_success(mocker):
    # Mock repositories and external integrations
    mock_save_lead = mocker.patch("app.db.leads_repo.save_lead")
    mock_update_lead = mocker.patch("app.db.leads_repo.update_lead")
    mock_get_lead = mocker.patch("app.db.leads_repo.get_lead")
    mock_get_lead.return_value = {
        "lead_id": "ivan-123",
        "first_name": "Ivan",
        "email": "ivan@techcorp.rs",
        "score_label": "hot",
        "score": 85,
        "intent_category": "automation",
        "owner": "oleg@workshop.ai",
        "company_name": "Techcorp",
    }
    mock_log_event = mocker.patch("app.db.events_repo.log_event")
    
    mock_find_duplicate = mocker.patch("app.services.deduper.find_duplicate")
    mock_find_duplicate.return_value = None
    
    mock_classify_intent = mocker.patch("app.services.enricher.classify_intent")
    mock_classify_intent.return_value = "automation"
    
    mock_score_lead = mocker.patch("app.services.enricher.score_lead")
    mock_score_lead.return_value = (85, "hot", "Enterprise size automation need")
    
    # Mock CRM factory and adapter
    mock_crm = mocker.MagicMock()
    mock_crm.is_configured.return_value = True
    
    from app.crm.base import CRMResult
    mock_crm.full_upsert = mocker.AsyncMock(return_value=CRMResult(
        contact_id="c-1", company_id="co-1", deal_id="d-1"
    ))
    
    mocker.patch("app.services.pipeline.get_crm_adapter", return_value=mock_crm)
    
    # Mock draft generator
    mock_generate_draft = mocker.patch("app.services.draft.generate_draft")
    mock_generate_draft.return_value = ("Draft Subject", "Draft Body text")
    
    # Mock alerts
    mock_send_alert = mocker.patch("app.services.alerts.send_new_lead_alert")
    
    raw_lead = {
        "first_name": "Ivan",
        "last_name": "Petrov",
        "email": "ivan@techcorp.rs",
        "inquiry_text": "We need custom hubspot integration to sync leads automated.",
    }
    
    # Run the pipeline
    lead = await process_lead(raw_lead)
    
    # Verify outputs and state
    assert lead.first_name == "Ivan"
    assert lead.email == "ivan@techcorp.rs"
    
    # Verify exact stages called
    mock_save_lead.assert_called_once()
    mock_find_duplicate.assert_called_once()
    mock_classify_intent.assert_called_once_with("We need custom hubspot integration to sync leads automated.")
    mock_score_lead.assert_called_once()
    mock_crm.full_upsert.assert_called_once()
    mock_generate_draft.assert_called_once()
    mock_send_alert.assert_called_once()
    
    # Verify database updates reflect pipeline states
    # It updates: intent_category, score details, crm ids, and draft replies.
    assert mock_update_lead.call_count >= 4
