"""amoCRM adapter — stub for v2 implementation."""
from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.crm.base import CRMAdapter, CRMResult

logger = logging.getLogger(__name__)


class AmoCRMAdapter(CRMAdapter):

    def _base(self) -> str:
        return f"https://{get_settings().amocrm_subdomain}.amocrm.ru/api/v4"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {get_settings().amocrm_token}",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        cfg = get_settings()
        return bool(cfg.amocrm_subdomain and cfg.amocrm_token)

    async def upsert_contact(self, lead: dict) -> CRMResult:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{self._base()}/contacts", headers=self._headers(), json=[{
                "first_name": lead.get("first_name", ""),
                "last_name": lead.get("last_name", ""),
                "custom_fields_values": [
                    {"field_code": "EMAIL", "values": [{"value": lead.get("email", "")}]},
                    {"field_code": "PHONE", "values": [{"value": lead.get("phone", "")}]},
                ],
            }])
            r.raise_for_status()
            contact_id = str(r.json()["_embedded"]["contacts"][0]["id"])
            return CRMResult(contact_id=contact_id)

    async def upsert_company(self, lead: dict) -> CRMResult:
        if not lead.get("company_name"):
            return CRMResult()
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{self._base()}/companies", headers=self._headers(), json=[{
                "name": lead.get("company_name", ""),
            }])
            r.raise_for_status()
            company_id = str(r.json()["_embedded"]["companies"][0]["id"])
            return CRMResult(company_id=company_id)

    async def upsert_deal(
        self, lead: dict, contact_id: str = "", company_id: str = ""
    ) -> CRMResult:
        payload: dict = {
            "name": f"{lead.get('first_name','')} {lead.get('company_name','Lead')} — AI Automation",
            "status_id": 142,  # default "new" pipeline stage
        }
        if contact_id:
            payload["_embedded"] = {"contacts": [{"id": int(contact_id)}]}

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{self._base()}/leads", headers=self._headers(), json=[payload])
            r.raise_for_status()
            deal_id = str(r.json()["_embedded"]["leads"][0]["id"])
            return CRMResult(deal_id=deal_id)

    async def create_task(self, lead: dict, deal_id: str, title: str) -> CRMResult:
        from datetime import datetime, timedelta, timezone
        due_ts = int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp())
        payload: dict = {
            "text": title,
            "complete_till": due_ts,
            "task_type_id": 1,
        }
        if deal_id:
            payload["entity_id"] = int(deal_id)
            payload["entity_type"] = "leads"

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{self._base()}/tasks", headers=self._headers(), json=[payload])
            r.raise_for_status()
            task_id = str(r.json()["_embedded"]["tasks"][0]["id"])
            return CRMResult(task_id=task_id)
