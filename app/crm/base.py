"""Abstract CRM adapter — all CRM connectors must implement this interface."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CRMResult:
    contact_id: str = ""
    company_id: str = ""
    deal_id: str = ""
    task_id: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


class CRMAdapter(ABC):
    """
    Abstract CRM connector.
    Each method is independently optional — implement as no-ops if CRM
    does not support the concept, but always return CRMResult.
    """

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if required credentials are present."""

    @abstractmethod
    async def upsert_contact(self, lead: dict) -> CRMResult:
        """Create or update a Contact. Returns CRMResult with contact_id."""

    @abstractmethod
    async def upsert_company(self, lead: dict) -> CRMResult:
        """Create or update a Company. Returns CRMResult with company_id."""

    @abstractmethod
    async def upsert_deal(
        self,
        lead: dict,
        contact_id: str = "",
        company_id: str = "",
    ) -> CRMResult:
        """Create or update a Deal/Opportunity. Returns CRMResult with deal_id."""

    @abstractmethod
    async def create_task(self, lead: dict, deal_id: str, title: str) -> CRMResult:
        """Create a follow-up task in CRM."""

    async def update_contact_status(self, contact_id: str, status: str) -> bool:
        """Update contact lead status in CRM. Return True on success."""
        return True

    async def log_outgoing_email(self, contact_id: str, subject: str, body: str) -> bool:
        """Log an outgoing email communication against the contact. Return True on success."""
        return True


    async def full_upsert(self, lead: dict) -> CRMResult:
        """
        Orchestrate full CRM write: contact → company → deal → task.
        Override in subclasses if the CRM has a single batch endpoint.
        """
        result = CRMResult()

        try:
            contact_res = await self.upsert_contact(lead)
            result.contact_id = contact_res.contact_id
        except Exception as e:
            result.error = f"contact: {e}"
            return result

        try:
            company_res = await self.upsert_company(lead)
            result.company_id = company_res.company_id
        except Exception:
            pass  # company is optional

        try:
            deal_res = await self.upsert_deal(lead, result.contact_id, result.company_id)
            result.deal_id = deal_res.deal_id
        except Exception as e:
            result.error = f"deal: {e}"
            return result

        try:
            task_res = await self.create_task(lead, result.deal_id, "Reply to lead")
            result.task_id = task_res.task_id
        except Exception:
            pass  # task is optional

        return result


class BaseHttpCRMAdapter(CRMAdapter, ABC):
    """
    Base HTTP CRM Adapter that manages a single, persistent httpx.AsyncClient.
    Provides automated connection pooling, common logging, and request logic.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15)
        return self._client

    @abstractmethod
    def _headers(self) -> dict:
        """Return authorization and content type headers."""

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        Execute an HTTP request with uniform timeouts, pooling, and logging.
        """
        client = self._get_client()
        headers = self._headers()
        if "headers" in kwargs:
            headers = {**headers, **kwargs.pop("headers")}

        logger.debug("CRM HTTP Request %s %s with kwargs %s", method, url, kwargs)
        try:
            r = await client.request(method, url, headers=headers, **kwargs)
            r.raise_for_status()
            return r
        except httpx.HTTPStatusError as e:
            logger.error("CRM HTTP Error %s %s [Status %d]: %s", method, url, e.response.status_code, e.response.text)
            raise
        except Exception as e:
            logger.error("CRM Network/Connection Error %s %s: %s", method, url, e)
            raise

    async def close(self) -> None:
        """Close the underlying client pool."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()


class _NullAdapter(CRMAdapter):
    """No-op adapter — used when CRM_PROVIDER=none."""

    def is_configured(self) -> bool:
        return True

    async def upsert_contact(self, lead: dict) -> CRMResult:
        return CRMResult(contact_id="null")

    async def upsert_company(self, lead: dict) -> CRMResult:
        return CRMResult(company_id="null")

    async def upsert_deal(self, lead: dict, contact_id: str = "", company_id: str = "") -> CRMResult:
        return CRMResult(deal_id="null")

    async def create_task(self, lead: dict, deal_id: str, title: str) -> CRMResult:
        return CRMResult(task_id="null")
