"""API endpoint tests using httpx AsyncClient against the FastAPI app."""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

# Minimal env so Settings doesn't fail validation
import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-long-enough-32ch")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "testpass123")

from app.main import app
from app.services.auth import sign_token


def _auth_cookie() -> dict:
    token = sign_token("admin", os.environ["SECRET_KEY"])
    return {"session_token": token}


@pytest.mark.asyncio
async def test_healthz_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_intake_lead_returns_202():
    payload = {
        "first_name": "Ivan",
        "last_name": "Petrov",
        "email": "ivan@techcorp.rs",
        "inquiry_text": "Need CRM automation",
        "source": "webform",
    }
    mock_lead = MagicMock()
    mock_lead.lead_id = "abc12345"
    mock_lead.owner = "oleg@workshop.ai"

    with patch("app.api.v1.leads.process_lead", new_callable=AsyncMock, return_value=mock_lead):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/leads", json=payload)

    assert resp.status_code == 202
    data = resp.json()
    assert data["lead_id"] == "abc12345"
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_list_leads_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/leads")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_leads_with_valid_session():
    with patch("app.db.leads_repo.list_leads", new_callable=AsyncMock, return_value=[]):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies=_auth_cookie(),
        ) as client:
            resp = await client.get("/api/v1/leads")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_lead_not_found():
    with patch("app.db.leads_repo.get_lead", new_callable=AsyncMock, return_value=None):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies=_auth_cookie(),
        ) as client:
            resp = await client.get("/api/v1/leads/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_lead_success():
    with patch("app.services.followup.approve_and_send", new_callable=AsyncMock, return_value=True):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies=_auth_cookie(),
        ) as client:
            resp = await client.post("/api/v1/leads/lead-001/approve")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_approve_lead_already_approved():
    with patch("app.services.followup.approve_and_send", new_callable=AsyncMock, return_value=False):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies=_auth_cookie(),
        ) as client:
            resp = await client.post("/api/v1/leads/lead-001/approve")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_status_invalid_value():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies=_auth_cookie(),
    ) as client:
        resp = await client.patch("/api/v1/leads/lead-001/status?status=invalid_status")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_intake_rejects_missing_required_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/leads", json={"first_name": "Ivan"})
    assert resp.status_code == 422
