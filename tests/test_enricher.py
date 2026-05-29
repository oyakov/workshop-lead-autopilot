from __future__ import annotations

import pytest
from app.services.enricher import classify_intent, score_lead, _rule_based_score, _score_to_label


@pytest.mark.asyncio
async def test_classify_intent(mocker):
    mock_chat = mocker.patch("app.llm.gateway.chat")
    
    # 1. Success mock
    mock_chat.return_value = "automation "
    intent = await classify_intent("I need custom integrations")
    assert intent == "automation"
    
    # 2. Unknown classification mock
    mock_chat.return_value = "garbage-word"
    intent = await classify_intent("hello there")
    assert intent == "other"
    
    # 3. Exception mock (fallback)
    mock_chat.side_effect = Exception("LLM connection timed out")
    intent = await classify_intent("Need software")
    assert intent == "other"


@pytest.mark.asyncio
async def test_score_lead_llm_success(mocker):
    mock_chat = mocker.patch("app.llm.gateway.chat")
    mock_chat.return_value = '{"score": 85, "label": "hot", "reason": "Enterprise size company with automated workflows need"}'
    
    lead = {
        "first_name": "Ivan",
        "email": "ivan@techcorp.rs",
        "company_name": "Techcorp",
        "inquiry_text": "Need robust pipeline automation",
        "intent_category": "automation"
    }
    
    score, label, reason = await score_lead(lead)
    
    assert score == 85
    assert label == "hot"
    assert "Enterprise size" in reason


@pytest.mark.asyncio
async def test_score_lead_llm_fallback(mocker):
    mock_chat = mocker.patch("app.llm.gateway.chat")
    mock_chat.side_effect = Exception("Service unavailable")
    
    lead = {
        "first_name": "Ivan",
        "email": "ivan@techcorp.rs",
        "company_domain": "techcorp.rs",
        "company_name": "Techcorp",
        "inquiry_text": "Need CRM automation which is quite important to us so we can respond faster to clients. We really need this up and running as soon as possible, thank you!",
        "phone": "+38111123456",
        "intent_category": "automation"
    }
    
    score, label, reason = await score_lead(lead)
    
    # Rule based score: 30 + 15 (business email/domain) + 15 (len(inquiry)>100) + 10 (company_name) + 10 (phone) + 10 (intent) = 90
    assert score == 90
    assert label == "hot"
    assert "Rule-based" in reason
