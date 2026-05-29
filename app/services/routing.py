"""Owner routing — assigns leads to sales team members."""
from __future__ import annotations

import threading

from app.config import get_settings

_lock = threading.Lock()
_counter = [0]


def assign_owner() -> str:
    """Round-robin assignment across configured owners list."""
    owners = get_settings().owner_list
    if not owners:
        return "unassigned"
    with _lock:
        idx = _counter[0] % len(owners)
        _counter[0] += 1
    return owners[idx]


def route_by_intent(intent: str) -> str | None:
    """
    Optional intent-based routing.
    Returns a specific owner email if a rule matches, else None (fall back to round-robin).
    
    Extend this to read from DB or config file for production use.
    """
    # Example: route pricing inquiries to first owner
    # intent_map = {"pricing": "sales@company.com"}
    # return intent_map.get(intent)
    return None


def get_owner(intent: str = "") -> str:
    routed = route_by_intent(intent)
    return routed or assign_owner()
