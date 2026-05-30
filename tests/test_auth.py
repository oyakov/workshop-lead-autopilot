"""Tests for HMAC-based auth token and session helpers."""
from __future__ import annotations

import pytest
from app.services.auth import sign_token, verify_token

SECRET = "test-secret-key-32chars-long-xyz!"


def test_sign_and_verify_valid_token():
    token = sign_token("admin", SECRET)
    result = verify_token(token, SECRET)
    assert result == "admin"


def test_verify_expired_token():
    token = sign_token("admin", SECRET, expires_in_seconds=-1)
    result = verify_token(token, SECRET)
    assert result is None


def test_verify_tampered_token():
    token = sign_token("admin", SECRET)
    tampered = token[:-1] + ("x" if token[-1] != "x" else "y")
    result = verify_token(tampered, SECRET)
    assert result is None


def test_verify_wrong_secret():
    token = sign_token("admin", SECRET)
    result = verify_token(token, "wrong-secret")
    assert result is None


def test_verify_malformed_token():
    assert verify_token("", SECRET) is None
    assert verify_token("noperiod", SECRET) is None
    assert verify_token("a.b.c", SECRET) is None
