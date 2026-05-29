from __future__ import annotations

import pytest
from app.crm.base import CRMAdapter, CRMResult, _NullAdapter
from app.crm.factory import get_crm_adapter
from app.config import Settings


class MockCRMAdapter(CRMAdapter):
    def __init__(self, fail_contact=False, fail_company=False, fail_deal=False, fail_task=False):
        self.fail_contact = fail_contact
        self.fail_company = fail_company
        self.fail_deal = fail_deal
        self.fail_task = fail_task

    def is_configured(self) -> bool:
        return True

    async def upsert_contact(self, lead: dict) -> CRMResult:
        if self.fail_contact:
            raise Exception("Failed upserting contact")
        return CRMResult(contact_id="contact-123")

    async def upsert_company(self, lead: dict) -> CRMResult:
        if self.fail_company:
            raise Exception("Failed upserting company")
        return CRMResult(company_id="company-123")

    async def upsert_deal(self, lead: dict, contact_id: str = "", company_id: str = "") -> CRMResult:
        if self.fail_deal:
            raise Exception("Failed upserting deal")
        return CRMResult(deal_id="deal-123")

    async def create_task(self, lead: dict, deal_id: str, title: str) -> CRMResult:
        if self.fail_task:
            raise Exception("Failed creating task")
        return CRMResult(task_id="task-123")


@pytest.mark.asyncio
async def test_crm_adapter_full_upsert_success():
    adapter = MockCRMAdapter()
    lead = {"email": "test@example.com"}
    
    result = await adapter.full_upsert(lead)
    
    assert result.ok
    assert result.contact_id == "contact-123"
    assert result.company_id == "company-123"
    assert result.deal_id == "deal-123"
    assert result.task_id == "task-123"
    assert not result.error


@pytest.mark.asyncio
async def test_crm_adapter_full_upsert_contact_fails():
    adapter = MockCRMAdapter(fail_contact=True)
    lead = {"email": "test@example.com"}
    
    result = await adapter.full_upsert(lead)
    
    assert not result.ok
    assert "contact" in result.error
    assert not result.contact_id


@pytest.mark.asyncio
async def test_crm_adapter_full_upsert_company_fails_continues():
    adapter = MockCRMAdapter(fail_company=True)
    lead = {"email": "test@example.com"}
    
    result = await adapter.full_upsert(lead)
    
    # Company is optional, so the full sync succeeds but company_id is empty
    assert result.ok
    assert result.contact_id == "contact-123"
    assert not result.company_id
    assert result.deal_id == "deal-123"
    assert result.task_id == "task-123"


@pytest.mark.asyncio
async def test_crm_adapter_full_upsert_deal_fails():
    adapter = MockCRMAdapter(fail_deal=True)
    lead = {"email": "test@example.com"}
    
    result = await adapter.full_upsert(lead)
    
    assert not result.ok
    assert "deal" in result.error
    assert result.contact_id == "contact-123"
    assert result.company_id == "company-123"
    assert not result.deal_id


@pytest.mark.asyncio
async def test_crm_adapter_full_upsert_task_fails_continues():
    adapter = MockCRMAdapter(fail_task=True)
    lead = {"email": "test@example.com"}
    
    result = await adapter.full_upsert(lead)
    
    # Task is optional, so full sync succeeds
    assert result.ok
    assert result.contact_id == "contact-123"
    assert result.company_id == "company-123"
    assert result.deal_id == "deal-123"
    assert not result.task_id


@pytest.mark.asyncio
async def test_null_adapter():
    adapter = _NullAdapter()
    assert adapter.is_configured()
    
    lead = {"email": "test@example.com"}
    result = await adapter.full_upsert(lead)
    
    assert result.ok
    assert result.contact_id == "null"
    assert result.company_id == "null"
    assert result.deal_id == "null"
    assert result.task_id == "null"


def test_crm_factory_returns_null_adapter(mocker):
    # Clear the lru_cache for testing
    get_crm_adapter.cache_clear()
    
    mocker.patch(
        "app.crm.factory.get_settings",
        return_value=Settings(crm_provider="none")
    )
    
    adapter = get_crm_adapter()
    assert isinstance(adapter, _NullAdapter)
