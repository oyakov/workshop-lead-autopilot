"""HubSpot Free CRM connector — creates Contact + Company + Deal per lead."""
import os
import httpx

BASE = "https://api.hubapi.com"


def _headers() -> dict:
    token = os.environ.get("HUBSPOT_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _post(path: str, body: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{BASE}{path}", json=body, headers=_headers())
        r.raise_for_status()
        return r.json()


async def _assoc(from_type: str, from_id: str, to_type: str, to_id: str, assoc_type: str):
    path = f"/crm/v4/objects/{from_type}/{from_id}/associations/{to_type}/{to_id}"
    body = [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": assoc_type}]
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.put(f"{BASE}{path}", json=body, headers=_headers())
        r.raise_for_status()


async def create_deal(lead: dict) -> str:
    """
    Creates a Deal in HubSpot (required scope: crm.objects.deals.write).
    Also attempts Contact + Company creation if scopes allow.
    Returns the HubSpot Deal ID.
    """
    deal_id = ""
    contact_id = ""
    company_id = ""

    # 1. Create Deal — primary, must succeed
    deal_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')} — {lead.get('company_name', 'Lead')}".strip(" —")
    deal = await _post("/crm/v3/objects/deals", {"properties": {
        "dealname": deal_name,
        "dealstage": "appointmentscheduled",
        "pipeline": "default",
        "description": lead.get("inquiry_text", "")[:500],
    }})
    deal_id = deal["id"]

    # 2. Create Contact — optional, skip on scope error
    try:
        contact = await _post("/crm/v3/objects/contacts", {"properties": {
            "firstname": lead.get("first_name", ""),
            "lastname": lead.get("last_name", ""),
            "email": lead.get("email", ""),
            "phone": lead.get("phone", ""),
        }})
        contact_id = contact["id"]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            contact_id = _extract_existing_id(e.response.text)
        # 403 scope error = silently skip

    # 3. Create Company — optional
    if lead.get("company_domain") or lead.get("company_name"):
        try:
            company = await _post("/crm/v3/objects/companies", {"properties": {
                "name": lead.get("company_name", lead.get("company_domain", "")),
                "domain": lead.get("company_domain", ""),
            }})
            company_id = company["id"]
        except httpx.HTTPStatusError:
            pass

    # 4. Associate Contact → Deal
    if contact_id and deal_id:
        try:
            await _assoc("contacts", contact_id, "deals", deal_id, "3")
        except Exception:
            pass

    # 5. Associate Company → Deal
    if company_id and deal_id:
        try:
            await _assoc("companies", company_id, "deals", deal_id, "5")
        except Exception:
            pass

    return deal_id


def _extract_existing_id(error_text: str) -> str:
    import re
    m = re.search(r'"id"\s*:\s*"(\d+)"', error_text)
    return m.group(1) if m else ""


def is_configured() -> bool:
    t = os.environ.get("HUBSPOT_TOKEN", "")
    return len(t) > 20
