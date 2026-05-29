from __future__ import annotations

import pytest
from app.services.deduper import find_duplicate


@pytest.mark.asyncio
async def test_find_duplicate_by_email_found(mocker):
    # Mock leads_repo
    mock_find = mocker.patch("app.db.leads_repo.find_by_email")
    mock_find.return_value = [
        {"lead_id": "lead-123", "email": "test@example.com"},
        {"lead_id": "lead-456", "email": "test@example.com"},
    ]
    
    mock_find_domain = mocker.patch("app.db.leads_repo.find_by_domain")
    
    # We are processing 'lead-456', and it matches 'lead-123'
    result = await find_duplicate("test@example.com", "example.com", "lead-456")
    
    assert result is not None
    assert result["lead_id"] == "lead-123"
    mock_find.assert_called_once_with("test@example.com")
    mock_find_domain.assert_not_called()


@pytest.mark.asyncio
async def test_find_duplicate_no_email_match_but_domain_logged(mocker):
    mock_find_email = mocker.patch("app.db.leads_repo.find_by_email")
    mock_find_email.return_value = []
    
    mock_find_domain = mocker.patch("app.db.leads_repo.find_by_domain")
    mock_find_domain.return_value = [
        {"lead_id": "lead-123", "company_domain": "example.com"}
    ]
    
    # Email doesn't match, domain matches but it should only be logged (return None)
    result = await find_duplicate("test@example.com", "example.com", "lead-456")
    
    assert result is None
    mock_find_email.assert_called_once_with("test@example.com")
    mock_find_domain.assert_called_once_with("example.com")
