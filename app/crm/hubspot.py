"""HubSpot CRM adapter — Contact + Company + Deal + Task."""
from __future__ import annotations

import re
import logging
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.crm.base import CRMAdapter, CRMResult

logger = logging.getLogger(__name__)

BASE = "https://api.hubapi.com"


class HubSpotAdapter(CRMAdapter):

    def is_configured(self) -> bool:
        return len(get_settings().hubspot_token) > 20

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {get_settings().hubspot_token}",
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, body: dict) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{BASE}{path}", json=body, headers=self._headers())
            r.raise_for_status()
            return r.json()

    async def _put(self, path: str, body: list) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.put(f"{BASE}{path}", json=body, headers=self._headers())
            r.raise_for_status()
            return r.json()

    def _extract_id_from_conflict(self, error_text: str) -> str:
        m = re.search(r'"id"\s*:\s*"(\d+)"', error_text)
        return m.group(1) if m else ""

    async def _associate(
        self, from_type: str, from_id: str, to_type: str, to_id: str, assoc_type_id: str
    ) -> None:
        path = f"/crm/v4/objects/{from_type}/{from_id}/associations/{to_type}/{to_id}"
        body = [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": assoc_type_id}]
        try:
            await self._put(path, body)
        except Exception as e:
            logger.debug("Association %s→%s failed (non-critical): %s", from_type, to_type, e)

    async def upsert_contact(self, lead: dict) -> CRMResult:
        try:
            res = await self._post("/crm/v3/objects/contacts", {"properties": {
                "firstname": lead.get("first_name", ""),
                "lastname": lead.get("last_name", ""),
                "email": lead.get("email", ""),
                "phone": lead.get("phone", ""),
            }})
            return CRMResult(contact_id=res["id"])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                cid = self._extract_id_from_conflict(e.response.text)
                return CRMResult(contact_id=cid)
            raise

    async def upsert_company(self, lead: dict) -> CRMResult:
        if not lead.get("company_domain") and not lead.get("company_name"):
            return CRMResult()
        try:
            res = await self._post("/crm/v3/objects/companies", {"properties": {
                "name": lead.get("company_name") or lead.get("company_domain", ""),
                "domain": lead.get("company_domain", ""),
            }})
            return CRMResult(company_id=res["id"])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                cid = self._extract_id_from_conflict(e.response.text)
                return CRMResult(company_id=cid)
            raise

    async def upsert_deal(
        self, lead: dict, contact_id: str = "", company_id: str = ""
    ) -> CRMResult:
        name = (
            f"{lead.get('first_name','')} {lead.get('last_name','')} "
            f"— {lead.get('company_name','Lead')}"
        ).strip(" —")

        res = await self._post("/crm/v3/objects/deals", {"properties": {
            "dealname": name,
            "dealstage": "appointmentscheduled",
            "pipeline": "default",
            "description": lead.get("inquiry_text", "")[:500],
            "hs_lead_status": "NEW",
        }})
        deal_id = res["id"]

        if contact_id:
            await self._associate("contacts", contact_id, "deals", deal_id, "3")
        if company_id:
            await self._associate("companies", company_id, "deals", deal_id, "5")

        return CRMResult(deal_id=deal_id)

    async def create_task(self, lead: dict, deal_id: str, title: str) -> CRMResult:
        due_ts = int(datetime.now(timezone.utc).timestamp() * 1000) + 86_400_000  # +24h ms
        try:
            res = await self._post("/crm/v3/objects/tasks", {"properties": {
                "hs_task_subject": title,
                "hs_task_status": "NOT_STARTED",
                "hs_task_type": "EMAIL",
                "hs_timestamp": str(due_ts),
                "hubspot_owner_id": "",
            }})
            task_id = res["id"]
            if deal_id:
                await self._associate("tasks", task_id, "deals", deal_id, "216")
            return CRMResult(task_id=task_id)
        except Exception as e:
            logger.warning("HubSpot task creation failed (non-critical): %s", e)
            return CRMResult()
