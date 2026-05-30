"""Tests for HMAC-signed unsubscribe token generation and verification."""
from __future__ import annotations

import pytest
from app.services.unsubscribe import make_unsubscribe_url, verify_unsubscribe_token

SECRET = "test-secret-xyz!"


def test_roundtrip_valid_token():
    url = make_unsubscribe_url("ivan@techcorp.rs", SECRET)
    token = url.split("token=")[1]
    email = verify_unsubscribe_token(token, SECRET)
    assert email == "ivan@techcorp.rs"


def test_case_normalised():
    url = make_unsubscribe_url("IVAN@TechCorp.RS", SECRET)
    token = url.split("token=")[1]
    email = verify_unsubscribe_token(token, SECRET)
    assert email == "ivan@techcorp.rs"


def test_tampered_token_rejected():
    url = make_unsubscribe_url("ivan@techcorp.rs", SECRET)
    token = url.split("token=")[1]
    bad = token[:-4] + "XXXX"
    assert verify_unsubscribe_token(bad, SECRET) is None


def test_wrong_secret_rejected():
    url = make_unsubscribe_url("ivan@techcorp.rs", SECRET)
    token = url.split("token=")[1]
    assert verify_unsubscribe_token(token, "wrong-secret") is None


def test_empty_token_rejected():
    assert verify_unsubscribe_token("", SECRET) is None


def test_url_contains_base_when_provided():
    url = make_unsubscribe_url("a@b.com", SECRET, base_url="https://myapp.com")
    assert url.startswith("https://myapp.com/api/v1/unsubscribe?token=")


def test_empty_email_returns_empty():
    url = make_unsubscribe_url("", SECRET)
    assert url == ""
