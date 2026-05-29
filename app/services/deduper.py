"""Deduplication — checks for existing leads by email or domain."""
from __future__ import annotations

import logging

from app.db import leads_repo

logger = logging.getLogger(__name__)


async def find_duplicate(email: str, domain: str, current_lead_id: str) -> dict | None:
    """
    Return the first existing lead that looks like a duplicate, or None.
    
    Priority:
    1. Exact email match (excluding current lead)
    2. Same company domain (excluding free domains) — secondary signal only
    """
    if email:
        existing = await leads_repo.find_by_email(email)
        dupes = [l for l in existing if l["lead_id"] != current_lead_id]
        if dupes:
            logger.info("Duplicate found by email=%s → %s", email, dupes[0]["lead_id"])
            return dupes[0]

    # Domain-based dedup only logged, not auto-marked (too many false positives)
    if domain:
        domain_matches = await leads_repo.find_by_domain(domain)
        domain_dupes = [l for l in domain_matches if l["lead_id"] != current_lead_id]
        if domain_dupes:
            logger.info(
                "Potential domain duplicate domain=%s → %s (not auto-closed)",
                domain,
                domain_dupes[0]["lead_id"],
            )

    return None
