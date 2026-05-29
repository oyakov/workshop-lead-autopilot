"""Pipedrive CRM adapter — stub implementation for v2."""
from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.crm.base import CRMAdapter, CRMResult

logger = logging.getLogger(__name__)

BASE = "https://{domain}.pipedrive.com/api/v1"


class PipedriveAdapter(CRMAdapter):

    def _base(self) -> str:
        return BASE.format(domain=get_settings().pipedrive_company_domain)

    def _params(self) -> dict:
        return {"api_token": get_settings().pipedrive_api_key}

    def is_configured(self) -> bool:
        cfg = get_settings()
        return bool(cfg.pipedrive_api_key and cfg.pipedrive_company_domain)

    async def upsert_contact(self, lead: dict) -> CRMResult:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{self._base()}/persons", params=self._params(), json={
                "name": f"{lead.get('first_name','')} {lead.get('last_name','')}".strip(),
                "email": [{"value": lead.get("email", ""), "primary": True}],
                "phone": [{"value": lead.get("phone", ""), "primary": True}],
            })
            r.raise_for_status()
            return CRMResult(contact_id=str(r.json()["data"]["id"]))

    async def upsert_company(self, lead: dict) -> CRMResult:
        if not lead.get("company_name"):
            return CRMResult()
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{self._base()}/organizations", params=self._params(), json={
                "name": lead.get("company_name", ""),
            })
            r.raise_for_status()
            return CRMResult(company_id=str(r.json()["data"]["id"]))

    async def upsert_deal(
        self, lead: dict, contact_id: str = "", company_id: str = ""
    ) -> CRMResult:
        payload: dict = {
            "title": f"{lead.get('first_name','')} {lead.get('company_name','Lead')} — AI Automation",
            "status": "open",
        }
        if contact_id:
            payload["person_id"] = int(contact_id)
        if company_id:
            payload["org_id"] = int(company_id)

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{self._base()}/deals", params=self._params(), json=payload)
            r.raise_for_status()
            return CRMResult(deal_id=str(r.json()["data"]["id"]))

    async def create_task(self, lead: dict, deal_id: str, title: str) -> CRMResult:
        from datetime import datetime, timedelta, timezone
        due = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M")
        payload: dict = {
            "subject": title,
            "type": "task",
            "due_date": due[:10],
            "due_time": due[11:],
        }
        if deal_id:
            payload["deal_id"] = int(deal_id)
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{self._base()}/activities", params=self._params(), json=payload)
            r.raise_for_status()
            return CRMResult(task_id=str(r.json()["data"]["id"]))
