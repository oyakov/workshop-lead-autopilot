# Scenario E — Local LLM (Privacy Mode) vs Cloud LLM Fallback

**Goal:** Demonstrate that the system operates with a fully local LLM (LM Studio / Gemma) for on-premise data privacy, and gracefully falls back to the cloud LLM (Gemini) when the local model is unavailable.  
**Expected outcome:** Draft replies are generated either by the local model or the cloud model; scoring and intent classification adapt transparently.

---

## Context

Many B2B clients have strict data residency requirements and cannot send customer inquiry texts to external cloud APIs. Lead-Ops Autopilot solves this with a **dual-gateway LLM architecture**: it first tries a primary endpoint (configurable), then automatically falls back to a secondary. Both the primary and fallback URLs, models, and API keys are independently configurable in `.env`.

---

## Architecture

```
Incoming Lead
     │
     ▼
LLM Gateway (app/llm/gateway.py)
     ├─► Primary: LM Studio (local, http://host.docker.internal:1234/v1)
     │       ↓ success → use response
     │       ↓ failure / timeout →
     └─► Fallback: Gemini API (cloud, api.openai.com compatible endpoint)
                 ↓ success → use response
                 ↓ failure → rule-based fallback (scoring only)
```

---

## Configuration

In `.env`:

```env
# Primary — local LM Studio (privacy mode)
LLM_BASE_URL=http://host.docker.internal:1234/v1
LLM_MODEL=google/gemma-4-e4b
LLM_API_KEY=lm-studio

# Fallback — Gemini cloud
LLM_FALLBACK_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_FALLBACK_MODEL=gemini-2.0-flash
LLM_FALLBACK_API_KEY=<your-gemini-api-key>
```

In `docker-compose.yml`, the container resolves the host machine via:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
environment:
  - LLM_BASE_URL=http://host.docker.internal:1234/v1
```

---

## Demo Steps

### Mode 1: Full Local LLM (Privacy Mode)

1. **Start LM Studio** on the host machine with `google/gemma-4-e4b` loaded and server running on port `1234`.
2. Submit a lead (use Scenario A payload with a new email).
3. Watch `draft_generated` event — body will contain a context-rich reply generated entirely on-device.
4. **Verify in logs:**
   ```
   docker logs lead-autopilot | grep "LLM"
   ```
   You should see primary endpoint requests with `200 OK` and no fallback messages.

### Mode 2: Cloud Fallback (Local Model Down)

1. **Stop LM Studio** or change `LLM_BASE_URL` to an invalid URL.
2. Submit a lead.
3. The gateway catches the connection error, logs a warning, and **automatically retries on the Gemini endpoint**.
4. `draft_generated` event still fires — lead processing completes normally.
5. **Verify in logs:**
   ```
   docker logs lead-autopilot | grep "fallback"
   ```
   You should see: `"LLM primary failed, trying fallback"`.

### Mode 3: Both LLMs Down (Rule-Based Fallback)

1. Set both `LLM_BASE_URL` and `LLM_FALLBACK_BASE_URL` to invalid URLs.
2. Submit a lead.
3. **Scoring** falls back to the rule-based heuristic engine (no LLM required).
4. **Draft** falls back to a static personalized template.
5. Lead still saves to DB and CRM — no crash, no data loss.

---

## Key Assertions

| Mode | Intent classified | Score produced | Draft generated | System crashes |
|------|:-:|:-:|:-:|:-:|
| Local LLM active | ✅ LLM | ✅ LLM | ✅ LLM | ❌ |
| Local down, cloud up | ✅ LLM | ✅ LLM | ✅ LLM | ❌ |
| Both down | ✅ `"other"` | ✅ Rule-based | ✅ Template | ❌ |

---

## What This Demonstrates

- **Full data sovereignty** — no customer data needs to leave the client's infrastructure
- **Zero single points of failure** — three progressive fallback layers ensure uptime
- **LLM-agnostic gateway** — swap any OpenAI-compatible endpoint (Ollama, vLLM, Azure OpenAI) by changing a single `.env` variable
- **Transparent degradation** — every fallback is logged to the event system; managers can see when LLM was unavailable
