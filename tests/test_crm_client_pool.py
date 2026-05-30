from __future__ import annotations

import httpx
import pytest
from app.crm.base import BaseHttpCRMAdapter, CRMResult


class SimpleHttpCRMAdapter(BaseHttpCRMAdapter):
    def is_configured(self) -> bool:
        return True

    def _headers(self) -> dict:
        return {"Authorization": "Bearer test-key", "Content-Type": "application/json"}

    async def upsert_contact(self, lead: dict) -> CRMResult:
        r = await self._request("POST", "https://api.example.com/contacts", json=lead)
        return CRMResult(contact_id=r.json()["id"])

    async def upsert_company(self, lead: dict) -> CRMResult:
        return CRMResult()

    async def upsert_deal(self, lead: dict, contact_id: str = "", company_id: str = "") -> CRMResult:
        return CRMResult()

    async def create_task(self, lead: dict, deal_id: str, title: str) -> CRMResult:
        return CRMResult()


@pytest.mark.asyncio
async def test_crm_adapter_client_reuse(mocker):
    adapter = SimpleHttpCRMAdapter()

    # Mock the client request method
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"id": "123"}
    mock_response.status_code = 200

    # Ensure client is created
    client1 = adapter._get_client()
    assert isinstance(client1, httpx.AsyncClient)

    # Calling it again should return the exact same instance (pooling)
    client2 = adapter._get_client()
    assert client1 is client2

    # Mock request execution on this client
    mocker.patch.object(client1, "request", return_value=mock_response)

    result = await adapter.upsert_contact({"name": "Oleg"})
    assert result.contact_id == "123"

    # Verify standard request headers were passed
    client1.request.assert_called_once_with(
        "POST",
        "https://api.example.com/contacts",
        headers={"Authorization": "Bearer test-key", "Content-Type": "application/json"},
        json={"name": "Oleg"},
    )

    # Shut down pool
    await adapter.close()
    assert client1.is_closed


@pytest.mark.asyncio
async def test_crm_adapter_http_error_handling(mocker):
    adapter = SimpleHttpCRMAdapter()
    client = adapter._get_client()

    # Mock http status error
    mock_response = mocker.MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    err = httpx.HTTPStatusError("Auth failed", request=mocker.MagicMock(), response=mock_response)

    mocker.patch.object(client, "request", side_effect=err)

    with pytest.raises(httpx.HTTPStatusError):
        await adapter.upsert_contact({"name": "Oleg"})

    await adapter.close()
