"""
Tests for authentication and public security features.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings


@pytest.fixture
def client():
    return TestClient(app)


def test_login_success(client):
    """Test successful login returns 200 and sets cookie."""
    cfg = get_settings()
    res = client.post(
        "/api/v1/auth/login",
        json={"username": cfg.admin_username, "password": cfg.admin_password}
    )
    assert res.status_code == 200
    assert res.json() == {"ok": True, "username": cfg.admin_username}
    assert "session_token" in res.cookies


def test_login_failure(client):
    """Test failed login returns 401 and does not set cookie."""
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-password"}
    )
    assert res.status_code == 401
    assert "session_token" not in res.cookies


def test_logout_success(client):
    """Test logout clears the cookie."""
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 200
    # Cookie should be cleared or deleted (max-age=0 or empty value)
    cookie = res.cookies.get("session_token")
    assert cookie is None or cookie == ""


def test_protected_leads_endpoint(client):
    """Test that administrative leads routes require authentication."""
    # Accessed without session token cookie
    res = client.get("/api/v1/leads")
    assert res.status_code == 401
    
    # Accessed with invalid session token
    client.cookies.set("session_token", "invalid_token_b64.invalid_sig")
    res = client.get("/api/v1/leads")
    assert res.status_code == 401


def test_public_intake_leads_endpoint(client):
    """Test that public lead intake remains open without authentication."""
    # Submit invalid lead just to verify the intake route parses it (returns 422 instead of 401)
    res = client.post("/api/v1/leads", json={"first_name": "Ivan"})
    # It returns 422 validation error (since email/inquiry are missing), not 401!
    assert res.status_code == 422


def test_protected_health_endpoint(client):
    """Test that health check route requires authentication."""
    res = client.get("/api/v1/health")
    assert res.status_code == 401


def test_webhook_token_protection(client):
    """Test that n8n webhook routes require and validate X-n8n-Token header."""
    cfg = get_settings()
    
    # Missing header
    res = client.post("/api/v1/webhooks/n8n/sla-check")
    assert res.status_code == 422  # Unprocessable due to missing header
    
    # Invalid token header
    res = client.post(
        "/api/v1/webhooks/n8n/sla-check",
        headers={"X-n8n-Token": "wrong-token"}
    )
    assert res.status_code == 401
    
    # Valid token header
    res = client.post(
        "/api/v1/webhooks/n8n/sla-check",
        headers={"X-n8n-Token": cfg.webhook_token}
    )
    # The webhook route should proceed and process (might return 200/OK)
    assert res.status_code == 200
    assert res.json()["ok"] is True
