import os
import re
from services.llm import chat

DRAFT_PROMPT = """You are an assistant for {agency_name}, an AI automation agency.

Write a short professional first-reply email (4-5 sentences max).

Client info:
- Name: {first_name} {last_name}
- Company: {company_name}
- Their message: "{inquiry_text}"

Instructions:
- Start with "Subject: " on the first line
- Reference their specific pain point
- Position {agency_name} as AI automation specialists
- Propose a 15-minute discovery call
- Sign as "The {agency_name} Team"
- Be warm but concise"""


async def generate_draft(lead: dict) -> tuple[str, str]:
    agency = os.environ.get("AGENCY_NAME", "Workshop")
    fallback_subject = f"Re: Your inquiry - {lead.get('first_name', 'there')}"
    fallback_body = (
        f"Hi {lead.get('first_name', 'there')},\n\n"
        f"Thanks for reaching out! We specialise in automating exactly the kind of workflows you described. "
        f"Would you be open to a quick 15-min call this week to map out the solution?\n\n"
        f"Best,\nThe {agency} Team"
    )
    try:
        text = await chat(
            [{"role": "user", "content": DRAFT_PROMPT.format(
                agency_name=agency,
                first_name=lead.get("first_name", ""),
                last_name=lead.get("last_name", ""),
                company_name=lead.get("company_name", "their company"),
                inquiry_text=lead.get("inquiry_text", "")[:400],
            )}],
            max_tokens=350
        )
        if not text:
            return fallback_subject, fallback_body

        lines = text.strip().splitlines()

        # Extract subject from first line
        subject = fallback_subject
        body_start = 0
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
                body_start = i + 1
                break

        body = "\n".join(lines[body_start:]).strip()

        # Clean up "[Your Name]" placeholder
        body = re.sub(r"\[Your Name\]", agency, body)
        body = re.sub(r"\[.*?\]", "", body).strip()

        if not body:
            return subject, fallback_body

        return subject, body

    except Exception:
        return fallback_subject, fallback_body
