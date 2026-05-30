"""Centralized local in-memory mock database for fallback/local execution."""
from __future__ import annotations

# Global in-memory storage containers
leads: dict[str, dict] = {}
events: list[dict] = []


def reset_db() -> None:
    """Clear all mock database contents to allow clean testing sweeps."""
    leads.clear()
    events.clear()
