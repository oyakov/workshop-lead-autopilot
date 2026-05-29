# Lead-to-CRM Autopilot

An enterprise B2B lead management system that automates the full lifecycle from intake to CRM sync — classifying intent, scoring leads, routing to owners, generating personalized follow-ups, and alerting your sales team in real time.

---

## What It Does

| Stage | What Happens |
|-------|--------------|
| **Intake** | Receives leads via web form API or IMAP email polling |
| **Normalize** | Cleans fields: lowercase email, domain extraction, country/timezone parsing |
| **Deduplicate** | Detects duplicates by email + company domain; closes duplicates before processing |
| **Enrich** | LLM classifies intent (`automation`, `integration`, `pricing`, `partnership`, `other`) and scores the lead 0–100 |
| **Route** | Assigns an owner via round-robin from the configured sales team |
| **CRM Sync** | Upserts contact, company, and deal into HubSpot / Pipedrive / amoCRM |
| **Draft** | LLM generates a personalized email draft for owner review |
| **Follow-up** | T+24h Telegram reminder; T+48h auto-send or approval prompt |
| **SLA Monitor** | Checks every 15 min; sends Telegram alert when leads breach the SLA window |
| **Audit Log** | Every event recorded with full context for traceability |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.115 + Uvicorn (async) |
| Database | Supabase (PostgreSQL) — in-memory fallback for local dev |
| LLM | Google Gemini 2.0 Flash Lite (primary) + OpenAI-compatible fallback |
| CRM | HubSpot, Pipedrive, amoCRM, or None (demo mode) |
| Scheduler | APScheduler (IMAP polling, SLA checks, follow-ups) |
| Alerts | Telegram Bot API |
| Automation | n8n (containerized workflow engine) |
| Frontend | Vue.js + Tailwind CSS dashboard (embedded static) |
| Testing | pytest + pytest-asyncio |
| Containers | Docker + Docker Compose |

---

## Quick Start

### Docker Compose (recommended)

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd workshop-lead-autopilot

# 2. Configure environment
cp .env.example .env
# Edit .env — set at minimum: GEMINI_API_KEY and CRM_PROVIDER

# 3. Start the stack
docker-compose up --build -d

# 4. Verify it's running
curl http://localhost:8080/health
```

Services:

| URL | Service |
|-----|---------|
| `http://localhost:8080` | Lead Autopilot dashboard + API |
| `http://localhost:8080/docs` | Swagger UI (interactive API docs) |
| `http://localhost:5678` | n8n workflow editor |

### Local Development (Python)

```bash
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate       # Windows
# source .venv/bin/activate    # macOS/Linux

pip install -r requirements.txt

cp .env.example .env
# Edit .env

uvicorn app.main:app --reload --port 8000
```

Access at `http://localhost:8000`.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in values. Below are the variables grouped by concern.

### App

```env
AGENCY_NAME=Vestint
ENVIRONMENT=development          # development | production
SECRET_KEY=change-me             # API authentication secret
```

### Database (Supabase)

```env
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<service-role-key>
```

Leave both empty to use the built-in in-memory store — no Supabase account needed for local development.

### LLM — Primary

```env
LLM_PROVIDER=gemini              # gemini | lmstudio | openai
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash-lite
```

### LLM — Fallback (optional)

If the primary provider fails, requests are retried against the fallback. Useful for local development with [LM Studio](https://lmstudio.ai).

```env
LLM_FALLBACK_PROVIDER=lmstudio
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=lm-studio
LLM_MODEL=google/gemma-3-4b
```

### CRM

```env
CRM_PROVIDER=hubspot             # hubspot | pipedrive | amocrm | none
HUBSPOT_TOKEN=pat-eu1-...        # HubSpot private app token
```

Use `CRM_PROVIDER=none` to run in demo mode without an external CRM.

### Email Intake (IMAP)

```env
IMAP_ENABLED=false
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=leads@yourcompany.com
IMAP_PASSWORD=app-password
IMAP_FOLDER=INBOX
IMAP_POLL_INTERVAL_SECONDS=60
```

### Email Sending (SMTP)

```env
SMTP_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=leads@yourcompany.com
SMTP_PASSWORD=app-password
SMTP_FROM=leads@yourcompany.com
```

### Follow-up & SLA

```env
FOLLOWUP_AUTO_SEND=true          # Auto-send at T+48h; false = request approval
SLA_HOURS=24                     # Hours before SLA breach alert fires
FOLLOWUP_CLIENT_HOURS=48         # Hours after intake before follow-up email sends
```

### Telegram Alerts

```env
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_IDS=-100123456789  # Comma-separated, include group chats with -
```

### Sales Team

```env
OWNERS=alice@yourcompany.com,bob@yourcompany.com
```

Leads are assigned round-robin across this list.

### Lead Scoring Thresholds

```env
SCORING_ENABLED=true
SCORE_HOT_THRESHOLD=70           # ≥ 70 → hot
SCORE_WARM_THRESHOLD=40          # ≥ 40 → warm (below → cold)
```

### n8n

```env
N8N_WEBHOOK_BASE_URL=http://n8n:5678
N8N_USER=admin
N8N_PASSWORD=changeme
```

---

## API Reference

Full interactive docs at `/docs` (Swagger) and `/redoc`.

### Submit a Lead

```http
POST /api/v1/leads
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane@acme.com",
  "company": "Acme Corp",
  "message": "We need to automate our lead pipeline — 50 reps, 2k leads/month.",
  "phone": "+1-555-0100",
  "source": "website"
}
```

### List Leads

```http
GET /api/v1/leads?status=new&limit=50
```

### Get Lead + Event Log

```http
GET /api/v1/leads/{lead_id}
GET /api/v1/leads/{lead_id}/events
```

### Update Lead Status

```http
PATCH /api/v1/leads/{lead_id}
Content-Type: application/json

{ "status": "connected" }
```

### Approve Draft

```http
POST /api/v1/leads/{lead_id}/approve-draft
```

### Trigger SLA Check (demo/testing)

```http
POST /api/v1/leads/trigger-sla-check
```

### Health

```http
GET /health
```

---

## Lead Scoring

Each lead is scored 0–100 by the LLM, then adjusted by rule-based signals:

| Signal | Adjustment |
|--------|-----------|
| Business email domain | +15 |
| Message length > 100 chars | +15 |
| Phone number provided | +10 |
| Intent keywords (automate, integrate, scale…) | +10 |
| Spam keywords (free, resume, cv, seo guest post, no budget…) | −40 |

Score labels:

| Range | Label |
|-------|-------|
| ≥ 70 | `hot` |
| 40 – 69 | `warm` |
| < 40 | `cold` |

Cold leads are not pushed to the CRM and do not trigger follow-up automations.

---

## CRM Sync Details

### HubSpot

- Upserts contact by email (handles 409 conflicts)
- Creates or links company record
- Creates deal in default pipeline
- Creates follow-up task assigned to owner
- Sets `hs_lead_status` = `NEW` on creation, `CONNECTED` on draft approval
- Logs email activity for "Last Contacted" timestamp sync

### Pipedrive

- Upserts person and organization records
- Creates deal with lead metadata

### amoCRM

- Creates/updates lead and contact records

### None (demo mode)

Skips all CRM calls. Useful for demos and local development without API credentials.

---

## Architecture

```
Web Form / IMAP Email
        │
        ▼
  POST /api/v1/leads
        │
        ▼
  pipeline.process_lead()
   ├── normalizer       — field cleanup
   ├── deduper          — duplicate check
   ├── enricher         — LLM intent + scoring
   ├── router           — owner assignment
   ├── CRM adapter      — upsert contact/deal
   ├── draft service    — LLM email draft
   └── alerts service   — Telegram notification
        │
        ▼
  APScheduler (background)
   ├── IMAP poller      — every 60s (configurable)
   ├── SLA checker      — every 15 min
   └── follow-up sender — T+24h reminder, T+48h send
        │
        ▼
  Event log → Supabase (or in-memory)
```

### LLM Gateway

Requests go to the primary provider (Gemini by default). On failure, the gateway automatically retries the fallback provider (LM Studio / OpenAI-compatible). If both fail, the system uses rule-based scoring and a template draft so no lead is ever dropped.

### CRM Adapter Pattern

All CRM providers implement the same abstract interface (`app/crm/base.py`). Switching providers is a single environment variable change — no code changes required.

---

## Project Structure

```
workshop-lead-autopilot/
├── app/
│   ├── main.py              # FastAPI entry point, scheduler setup
│   ├── config.py            # Pydantic settings (all env vars)
│   ├── api/v1/
│   │   ├── leads.py         # Lead CRUD + pipeline actions
│   │   ├── health.py        # Health check
│   │   └── webhooks.py      # n8n webhook handlers
│   ├── services/
│   │   ├── pipeline.py      # Main orchestrator
│   │   ├── enricher.py      # Intent classification + scoring
│   │   ├── routing.py       # Round-robin owner assignment
│   │   ├── normalizer.py    # Field cleanup
│   │   ├── deduper.py       # Duplicate detection
│   │   ├── draft.py         # Email draft generation
│   │   ├── followup.py      # Follow-up scheduling + sending
│   │   ├── sla.py           # SLA breach detection
│   │   ├── imap_intake.py   # IMAP email poller
│   │   └── alerts.py        # Telegram notifications
│   ├── crm/
│   │   ├── base.py          # Abstract CRM interface
│   │   ├── factory.py       # Provider selection
│   │   ├── hubspot.py       # HubSpot implementation
│   │   ├── pipedrive.py     # Pipedrive implementation
│   │   └── amocrm.py        # amoCRM implementation
│   ├── llm/
│   │   ├── gateway.py       # Primary + fallback LLM router
│   │   ├── gemini.py        # Gemini implementation
│   │   ├── openai_compat.py # OpenAI-compatible implementation
│   │   └── prompts.py       # System prompts
│   ├── db/
│   │   ├── client.py        # Supabase async client (in-memory fallback)
│   │   ├── leads_repo.py    # Leads CRUD
│   │   └── events_repo.py   # Event log CRUD
│   └── static/
│       └── index.html       # Vue.js dashboard
├── tests/                   # pytest unit tests (20+ tests)
├── n8n/                     # n8n workflow definitions
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── postman_collection.json  # API test collection
└── seed_demo.py             # Demo data seeder
```

---

## Running Tests

```bash
# Activate venv first
pytest tests/ -v
```

Test coverage spans:

- Lead pipeline orchestration (`test_pipeline.py`)
- CRM adapter contract (`test_crm_adapter.py`)
- Intent classification and scoring (`test_enricher.py`)
- LLM gateway fallback logic (`test_llm_gateway.py`)
- Field normalization (`test_normalizer.py`)
- Duplicate detection (`test_deduper.py`)

---

## Using LM Studio (Local LLM)

1. Download and install [LM Studio](https://lmstudio.ai)
2. Load a model (e.g. `google/gemma-3-4b-it`)
3. Start the local inference server on port `1234`
4. Set in `.env`:

```env
LLM_FALLBACK_PROVIDER=lmstudio
LLM_BASE_URL=http://host.docker.internal:1234/v1   # from inside Docker
# or http://localhost:1234/v1                        # when running locally
LLM_API_KEY=lm-studio
LLM_MODEL=google/gemma-3-4b-it
```

---

## Seeding Demo Data

```bash
python seed_demo.py
```

Inserts a set of sample leads with varied scores, statuses, and intents for dashboard previewing.

---

## Production Checklist

- [ ] Set a strong `SECRET_KEY`
- [ ] Use real Supabase credentials (not in-memory)
- [ ] Set `N8N_PASSWORD` to something other than `changeme`
- [ ] Enable `TELEGRAM_ENABLED=true` and configure `TELEGRAM_BOT_TOKEN`
- [ ] Set `SMTP_ENABLED=true` with a real SMTP account
- [ ] Set `IMAP_ENABLED=true` if you want email intake
- [ ] Configure `OWNERS` with your actual sales team emails
- [ ] Set `ENVIRONMENT=production`
- [ ] Restrict `CORS_ORIGINS` in `app/main.py` to your frontend domain
- [ ] Review `SLA_HOURS` and `FOLLOWUP_CLIENT_HOURS` for your team's SLA targets
- [ ] Never commit `.env` to version control

---

## License

MIT
