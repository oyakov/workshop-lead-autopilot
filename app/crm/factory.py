"""CRM adapter factory — returns the configured CRM implementation."""
from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.crm.base import CRMAdapter


@lru_cache(maxsize=1)
def get_crm_adapter() -> CRMAdapter:
    provider = get_settings().crm_provider.lower()
    match provider:
        case "hubspot":
            from app.crm.hubspot import HubSpotAdapter
            return HubSpotAdapter()
        case "pipedrive":
            from app.crm.pipedrive import PipedriveAdapter
            return PipedriveAdapter()
        case "amocrm":
            from app.crm.amocrm import AmoCRMAdapter
            return AmoCRMAdapter()
        case "none":
            from app.crm.base import _NullAdapter
            return _NullAdapter()
        case _:
            raise ValueError(f"Unknown CRM_PROVIDER: {provider!r}. Valid: hubspot, pipedrive, amocrm, none")
