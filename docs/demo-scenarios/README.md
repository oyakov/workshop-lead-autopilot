# Demo Scenarios — Index

This directory contains step-by-step demo scripts for the **Lead-Ops Autopilot** system.  
Each scenario is self-contained and can be run independently (except where prerequisites are noted).

---

## Prerequisites

- Docker stack running: `docker-compose up -d`
- Dashboard accessible at: `http://localhost:8080`
- Telegram bot configured in `.env` (for alert scenarios)
- HubSpot Private App Token with CRM scopes (for CRM scenarios)

---

## Scenarios

| # | File | Title | What it Demonstrates |
|---|------|--------|---------------------|
| A | [scenario-a-enterprise-hot-lead.md](./scenario-a-enterprise-hot-lead.md) | Enterprise Hot Lead (Happy Path) | Full pipeline: intake → LLM scoring → HubSpot CRM → AI draft → Telegram alert → Human approval |
| B | [scenario-b-duplicate-detection.md](./scenario-b-duplicate-detection.md) | Duplicate Lead Detection | Exact email match blocks re-submission; CRM and LLM skipped |
| C | [scenario-c-spam-cold-lead-blocked.md](./scenario-c-spam-cold-lead-blocked.md) | Spam / Cold Lead Blocked | Keyword penalty drops score to `cold`; CRM write skipped automatically |
| D | [scenario-d-sla-breach-alert.md](./scenario-d-sla-breach-alert.md) | SLA Breach Alert | Overdue lead triggers 🔴 Telegram alert; duplicate suppression within 6h |
| E | [scenario-e-local-llm-privacy-mode.md](./scenario-e-local-llm-privacy-mode.md) | Local LLM Privacy Mode | Three-layer LLM fallback: local model → cloud Gemini → rule-based engine |

---

## Recommended Demo Order

For a client presentation, run the scenarios in this order for maximum impact:

1. **A** — Show the "wow" happy path first: a hot enterprise lead goes through the entire system in seconds
2. **B** — Show data hygiene: the same contact can't flood the CRM
3. **C** — Show spam protection: low-quality submissions are auto-filtered
4. **D** — Show accountability: overdue leads get escalated automatically
5. **E** — Show the privacy argument: the entire system can run 100% on-premise

---

## API Base URL

All API calls use the prefix `/api/v1/`. Local base URL: `http://localhost:8080/api/v1/`

### Quick Reference

| Action | Method | Path |
|--------|--------|------|
| Submit lead | `POST` | `/api/v1/leads` |
| List all leads | `GET` | `/api/v1/leads` |
| Get lead detail | `GET` | `/api/v1/leads/{lead_id}` |
| Get event log | `GET` | `/api/v1/leads/{lead_id}/events` |
| Approve draft | `POST` | `/api/v1/leads/{lead_id}/approve` |
| Trigger SLA check | `POST` | `/api/v1/leads/{lead_id}/sla-check` |
| Update status | `PATCH` | `/api/v1/leads/{lead_id}/status` |
| Health check | `GET` | `/api/v1/health` |

---

## Resetting Between Demos

To clear all leads between scenarios (restores a clean slate):

```powershell
docker-compose restart app
```

This resets the in-memory database. Supabase-backed deployments require a manual table truncation.
