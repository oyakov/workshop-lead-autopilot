# Scenario A — Enterprise Hot Lead (Happy Path)

**Goal:** Demonstrate the full end-to-end pipeline for a high-value enterprise lead.  
**Expected outcome:** Lead scored `hot`, pushed to HubSpot CRM, AI draft generated, Telegram alert fired.

---

## Context

An enterprise buyer from a tech company submits an inquiry about building a custom HubSpot integration to sync leads automatically. They use a corporate email, provide their company name, and write a detailed multi-sentence request. This is the best-case scenario that exercises every stage of the pipeline.

---

## Steps

### 1. Submit the Lead

**Endpoint:** `POST /api/v1/leads`  
**Dashboard:** Use the "Submit New Lead" panel on `http://localhost:8080`

```json
{
  "first_name": "Ivan",
  "last_name": "Petrov",
  "email": "ivan@techcorp.rs",
  "company_name": "TechCorp",
  "phone": "+381 63 123 4567",
  "inquiry_text": "Hi, we are a 120-person tech company and we need a custom HubSpot integration to automatically sync our inbound leads from three different web forms and route them to the right sales rep based on territory. We also want lead scoring based on company size and intent. What are your rates and how quickly can you start?"
}
```

### 2. Observe the Pipeline

Open the lead detail page and watch the **System Event Log** populate in real time:

| # | Event | Description |
|---|-------|-------------|
| 1 | `lead_received` | Lead assigned a UUID, persisted to DB |
| 2 | `lead_normalized` | Email normalized, domain extracted (`techcorp.rs`), owner assigned |
| 3 | `lead_intent_classified` | LLM identifies intent as `integration` |
| 4 | `lead_scored` | Score ~85–92/100, label `hot` — enterprise size, detailed inquiry, corporate domain |
| 5 | `crm_upsert_success` | Contact, Company, and Deal created in HubSpot |
| 6 | `draft_generated` | LLM generates a hyper-personalized reply referencing their specific pain points |
| 7 | `human_approval_requested` | Draft awaits manager approval |

### 3. Check Telegram

A 🔥 **New Lead** notification fires automatically:

```
🔥 New Lead [HOT 88/100]
Name: Ivan Petrov (TechCorp)
Intent: integration
Owner: oleg@workshop.ai
ID: <lead-id>
```

### 4. Approve the Draft

Click **✓ Approve & Send** on the dashboard or call:

```
POST /api/v1/leads/{lead_id}/approve
```

**What happens:**
- Lead status transitions `new` → `contacted`
- HubSpot contact `hs_lead_status` updated to `CONNECTED`
- An outgoing email activity is logged in HubSpot (populates **Last Contacted** date)

---

## Key Assertions

| Assertion | Expected |
|-----------|----------|
| Score label | `hot` |
| HubSpot contact created | ✅ |
| HubSpot deal created | ✅ |
| Telegram notification fired | ✅ |
| Draft subject contains lead name | ✅ |
| Status after approval | `contacted` |
| HubSpot `hs_lead_status` after approval | `CONNECTED` |

---

## What This Demonstrates

- **LLM intent classification** — "custom HubSpot integration" correctly maps to `integration`
- **LLM scoring** — enterprise signals (team size, phone, detailed inquiry, corporate domain) push score high
- **CRM-agnostic architecture** — same pipeline works with Pipedrive by switching `CRM_PROVIDER` in `.env`
- **Human-in-the-Loop** — manager sees a fully drafted reply; approval is one click
- **HubSpot activity sync** — Last Contacted auto-populates on approval
