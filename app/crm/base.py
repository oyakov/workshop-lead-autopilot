"""Abstract CRM adapter — all CRM connectors must implement this interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
