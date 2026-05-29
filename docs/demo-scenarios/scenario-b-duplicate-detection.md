# Scenario B — Duplicate Lead Detection

**Goal:** Demonstrate the deduplication engine blocking a second submission from the same contact.  
**Expected outcome:** Second submission is automatically closed as `closed_lost`, CRM is NOT called again, no Telegram alert.

---

## Context

A lead already exists in the system with email `ivan@techcorp.rs`. When the same person (or a colleague using the same email) submits again, the system detects the duplicate and short-circuits the pipeline immediately after persistence.

---

## Prerequisites

- Scenario A must have been completed first (Ivan Petrov with `ivan@techcorp.rs` is already in the DB).
- Alternatively, if you reset the DB, submit Scenario A first and then immediately try a second submission.

---

## Steps

### 1. Re-submit with the Same Email

**Endpoint:** `POST /api/v1/leads`

```json
{
  "first_name": "Ivan",
  "last_name": "Petrov",
  "email": "ivan@techcorp.rs",
  "company_name": "TechCorp",
  "inquiry_text": "Following up on my earlier message. Are you available for a call next week?"
}
```

### 2. Observe the Pipeline — Early Exit

The event log will be short:

| # | Event | Description |
|---|-------|-------------|
| 1 | `lead_received` | New lead UUID created and saved |
| 2 | `lead_normalized` | Domain extracted |
| 3 | `lead_deduped` | Match found by exact email → pipeline exits |

**No further events.** LLM calls, CRM write, draft generation, and Telegram alert are all skipped.

### 3. Check Lead Status

```
GET /api/v1/leads/{new_lead_id}
```

Expected response fields:

```json
{
  "status": "closed_lost",
  "draft_body": "DUPLICATE of <original_lead_id>"
}
```

---

## Key Assertions

| Assertion | Expected |
|-----------|----------|
| New lead status | `closed_lost` |
| `draft_body` content | `DUPLICATE of <original_lead_id>` |
| LLM called | ❌ No |
| HubSpot called | ❌ No |
| Telegram fired | ❌ No |
| Event log length | 3 events only |

---

## Deduplication Logic Details

The deduper checks in priority order:

1. **Exact email match** (hard block — pipeline exits immediately)
2. **Same company domain** on non-free domains (soft signal — logged only, not auto-closed)

This means `user1@bigcorp.com` and `user2@bigcorp.com` will both proceed normally (domain match is a warning only), but a second submission from `user1@bigcorp.com` itself is hard-blocked.

---

## What This Demonstrates

- **Cost protection** — LLM API calls and CRM writes are not wasted on known contacts
- **Data hygiene** — CRM is not polluted with duplicate contacts or deals
- **Full auditability** — the deduplication event is recorded in the event log with a reference to the original lead ID
- **Zero configuration** — deduplication is always-on by default
