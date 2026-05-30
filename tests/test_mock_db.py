from __future__ import annotations

import pytest
from app.db import mock_db


def test_mock_db_operations():
    # Ensure it's clean initially
    mock_db.reset_db()
    assert len(mock_db.leads) == 0
    assert len(mock_db.events) == 0

    # Add mock data
    mock_db.leads["lead-1"] = {"email": "hello@example.com"}
    mock_db.events.append({"lead_id": "lead-1", "event_type": "intake"})

    assert len(mock_db.leads) == 1
    assert len(mock_db.events) == 1

    # Reset
    mock_db.reset_db()
    assert len(mock_db.leads) == 0
    assert len(mock_db.events) == 0
