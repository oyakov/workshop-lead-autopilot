# Scenario C — Spam / Cold Lead Blocked from CRM

**Goal:** Demonstrate that low-quality or spam submissions are automatically scored as `cold` and never reach the CRM.  
**Expected outcome:** Lead scored `cold`, CRM upsert skipped, no deal created in HubSpot, no Telegram alert.

---

## Context

Not all form submissions are genuine leads. Job seekers, SEO guest-post spammers, and "no-budget" tire-kickers waste sales team time and pollute the CRM. The scoring engine applies a keyword penalty (`-40` points) when spam signals are detected, dropping the score well below the warm threshold.

---

## Steps

### 1. Submit a Spam Lead

**Endpoint:** `POST /api/v1/leads`

**Example 1 — Job Seeker:**
```json
{
  "first_name": "Anna",
  "last_name": "Müller",
  "email": "anna.muller@gmail.com",
  "inquiry_text": "Hello, I'm looking for a job opportunity at your company. Please find attached my CV and resume. I have 3 years experience."
}
```

**Example 2 — SEO Spammer:**
```json
{
  "first_name": "Marketing",
  "last_name": "Team",
  "email": "seo@linksrus.com",
  "inquiry_text": "Hi, we offer seo guest post opportunities on high DA sites. This is completely free for your first article."
}
```

**Example 3 — No-Budget Inquiry:**
```json
{
  "first_name": "Carlos",
  "last_name": "Santos",
  "email": "carlos@gmail.com",
  "inquiry_text": "Can you build me a CRM integration for free? No budget but great exposure. Let me know."
}
```

### 2. Observe the Pipeline

| # | Event | Description |
|---|-------|-------------|
| 1 | `lead_received` | Lead persisted |
| 2 | `lead_normalized` | Fields cleaned |
| 3 | `lead_intent_classified` | LLM or rules classify intent |
| 4 | `lead_scored` | Spam keyword penalty applied; score drops to `<25`, label = `cold` |
| 5 | `crm_upsert_skipped` | CRM write blocked: `"reason": "Lead is cold/spam"` |
| 6 | `draft_generated` | Draft still generated (may be useful for tracking) |
| 7 | `human_approval_requested` | Awaits manager review (optional disposition) |

> **Note:** No Telegram alert fires for `cold` leads.

### 3. Verify CRM is Clean

Log in to HubSpot and confirm no contact, company, or deal was created for the spam submission. The lead exists only in the internal Supabase/in-memory database.

---

## Spam Keyword Penalty List

The following keywords trigger a `-40` point penalty:

| Keyword | Typical Source |
|---------|---------------|
| `free` | No-budget requests, SEO spam |
| `no budget` | Tire-kickers |
| `for free` | Variant |
| `job application` | Job seekers |
| `career` | Job seekers |
| `resume` | Job seekers |
| `cv` | Job seekers |
| `seo guest post` | Link-building spam |

The penalty is applied on top of the rule-based baseline, ensuring the final score stays at or below 25 (`cold` threshold).

---

## Scoring Thresholds (Defaults)

| Label | Score Range |
|-------|-------------|
| `hot` | ≥ 75 |
| `warm` | ≥ 45 |
| `cold` | < 45 |

These thresholds are configurable via `SCORE_HOT_THRESHOLD` and `SCORE_WARM_THRESHOLD` in `.env`.

---

## Key Assertions

| Assertion | Expected |
|-----------|----------|
| Score label | `cold` |
| Event `crm_upsert_skipped` present | ✅ |
| HubSpot contact created | ❌ No |
| HubSpot deal created | ❌ No |
| Telegram fired | ❌ No |

---

## What This Demonstrates

- **Automatic spam filtering** — no manual triage required from the sales team
- **CRM hygiene at scale** — the CRM remains clean; only genuine prospects reach it
- **Transparent scoring** — the `score_reason` field in the event log explains exactly which penalty was applied
- **Configurable thresholds** — the team can tune sensitivity via environment variables without code changes
