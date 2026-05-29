# Scenario D — SLA Breach Alert

**Goal:** Demonstrate the SLA breach detection and Telegram alert for an uncontacted lead.  
**Expected outcome:** A lead that was not actioned within the SLA window triggers a 🔴 Telegram alert.

---

## Context

Every lead that enters the pipeline has a `next_action_due_at` timestamp set to `now + SLA_HOURS` (default: 4 hours). If the lead is not contacted before this deadline, the SLA monitor fires and sends a Telegram alert to the owner, then logs an `alert_sla_breached` event. This ensures no lead falls through the cracks.

---

## Steps

### 1. Submit a New Lead (or Reuse Existing)

First, ensure there is a lead in the system with status `new` (not yet approved/contacted). Use Scenario A's payload with a different email to avoid deduplication:

```json
{
  "first_name": "Petra",
  "last_name": "Novak",
  "email": "petra@industrials-eu.com",
  "company_name": "Industrials EU",
  "inquiry_text": "We need to automate our entire sales pipeline from web form submissions to deal creation in our CRM. Interested in a discovery call."
}
```

Note the `lead_id` returned.

### 2. Force the SLA Breach

The demo endpoint instantly backdates the `next_action_due_at` to the past and triggers the SLA check:

```
POST /api/v1/leads/{lead_id}/sla-check
```

Or from the dashboard, use the **"Trigger SLA Breach"** button (sets due date to year 2000 and runs the checker).

### 3. Observe the SLA Check

**API Response:**
```json
{
  "ok": true,
  "breached_count": 1
}
```

**Event Log — new entry added:**

| # | Event | Description |
|---|-------|-------------|
| … | `alert_sla_breached` | Logged with owner, status, and overdue timestamp |

### 4. Check Telegram

A 🔴 **SLA Breach** notification fires:

```
🔴 SLA Breach
Lead: Petra Novak (Industrials EU)
Owner: oleg@workshop.ai
Status: new
Due: 2000-01-01T00:00:00+00:00
ID: <lead_id>
```

### 5. Duplicate Alert Protection

If you call the SLA check again within **6 hours**, no second alert fires. The system checks `alert_sla_breached` events and suppresses duplicates to prevent alert fatigue.

---

## Background SLA Scheduler

In production, the SLA check runs **automatically on a schedule** (every 15 minutes by default, configurable via `SLA_CHECK_INTERVAL_SECONDS`). The `/sla-check` endpoint is only for demo and manual testing.

**Scheduler setup** (from `app/main.py`):
```python
scheduler.add_job(check_sla, "interval", seconds=cfg.sla_check_interval_seconds)
```

---

## Key Assertions

| Assertion | Expected |
|-----------|----------|
| `breached_count` | 1 |
| `alert_sla_breached` event logged | ✅ |
| Telegram SLA alert fired | ✅ |
| Second alert within 6h | ❌ Suppressed |
| Lead status unchanged | `new` (SLA check is non-mutating) |

---

## What This Demonstrates

- **Zero-miss guarantee** — overdue leads are caught automatically even if managers are busy
- **Owner accountability** — each alert includes the assigned owner's name
- **Alert fatigue prevention** — built-in 6-hour deduplication for repeat breaches
- **Configurable SLA window** — `SLA_HOURS` in `.env` sets the response time requirement
