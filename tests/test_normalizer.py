from __future__ import annotations

import pytest
from app.services.normalizer import extract_domain, normalize_phone, normalize_email, normalize_lead


def test_normalize_email():
    assert normalize_email("  Test@Example.Com  ") == "test@example.com"


def test_normalize_phone():
    assert normalize_phone("+381 (11) 123-456") == "+38111123456"
    assert normalize_phone("123abc456") == "123456"


def test_extract_domain():
    # Corporate email
    assert extract_domain("ivan@techcorp.rs") == "techcorp.rs"
    # Free email domains should return empty string
    assert extract_domain("ivan@gmail.com") == ""
    assert extract_domain("oleg@yahoo.com") == ""
    # Invalid domain
    assert extract_domain("invalid-email") == ""


def test_normalize_lead():
    raw_lead = {
        "first_name": "  ivan ",
        "last_name": " petrov  ",
        "email": "  IVAN@techcorp.rs ",
        "phone": "+381 11-123-456",
        "inquiry_text": "  Need CRM automation  "
    }
    
    normalized = normalize_lead(raw_lead)
    
    assert normalized["first_name"] == "Ivan"
    assert normalized["last_name"] == "Petrov"
    assert normalized["email"] == "ivan@techcorp.rs"
    assert normalized["phone"] == "+38111123456"
    assert normalized["company_domain"] == "techcorp.rs"
    assert normalized["company_name"] == "Techcorp"
    assert normalized["inquiry_text"] == "Need CRM automation"
