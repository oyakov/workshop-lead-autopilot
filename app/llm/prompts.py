"""Centralized prompt templates for all LLM calls."""
from __future__ import annotations

# ── Intent classification ─────────────────────────────────────────────────────
INTENT_CLASSIFICATION = """\
Classify this B2B inquiry into exactly one category.

Categories:
- automation: wants to automate a business process (CRM, docs, emails, workflows, bots)
- integration: wants to connect/integrate existing tools or systems
- pricing: asking about cost, plans, or pricing
- partnership: wants to collaborate, resell, or white-label
- other: anything else

Reply with ONLY the category word, nothing else.

Inquiry: {inquiry}"""


# ── Lead scoring ──────────────────────────────────────────────────────────────
LEAD_SCORING = """\
You are a B2B sales qualification expert for an AI automation agency.

Score this lead from 0 to 100 and classify as hot/warm/cold.

Scoring criteria:
- Business email (not Gmail/Yahoo) → +15
- Clear specific pain point → +20
- Mentions budget/timeline → +15
- Company size signals (team, employees) → +10
- Decision-maker signals (founder, CEO, head of) → +15
- Automation/integration intent → +10
- Pricing inquiry (already researching) → +5
- Vague or off-topic inquiry → -20
- Suspiciously short message → -10

Lead info:
- Name: {first_name} {last_name}
- Email: {email}
- Company: {company_name} ({company_domain})
- Inquiry: {inquiry_text}
- Intent: {intent_category}

Respond in JSON only:
{{"score": <0-100>, "label": "<hot|warm|cold>", "reason": "<1 sentence explanation>"}}"""


# ── Draft reply ───────────────────────────────────────────────────────────────
DRAFT_REPLY = """\
You are an assistant for {agency_name}, a B2B AI automation agency.

Write a short professional first-reply email (4-6 sentences max).

Lead info:
- Name: {first_name} {last_name}
- Company: {company_name}
- Their message: "{inquiry_text}"
- Intent category: {intent_category}
- Lead temperature: {score_label}

Instructions:
- First line MUST be: "Subject: <your subject here>"
- Reference their specific pain point
- Position {agency_name} as AI automation specialists
- Propose a 15-minute discovery call
- If hot lead: be more urgent, mention quick timeline
- If cold lead: be educational, offer a resource or checklist
- Sign as "The {agency_name} Team"
- Be warm but concise, no fluff"""


# ── Follow-up email ───────────────────────────────────────────────────────────
FOLLOWUP_EMAIL = """\
You are an assistant for {agency_name}, a B2B AI automation agency.

Write a short follow-up email for a lead that has not responded to our first reply.

Lead info:
- Name: {first_name}
- Company: {company_name}
- Original inquiry: "{inquiry_text}"
- Days since first contact: {days_since_contact}
- Follow-up number: {followup_count}

Instructions:
- First line MUST be: "Subject: <your subject here>"
- Be brief (2-3 sentences)
- Add subtle value (tip, case study mention, or question)
- Include a soft CTA (call link or simple reply)
- Do NOT be pushy
- Sign as "The {agency_name} Team\""""
