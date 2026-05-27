"""Seed 3 realistic demo leads for sales calls."""
import asyncio, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from services.db import init_db
from services.pipeline import process_lead

DEMO_LEADS = [
    {
        "first_name": "Marko",
        "last_name": "Jovanovic",
        "email": "marko@delta-consulting.rs",
        "company_name": "Delta Consulting",
        "inquiry_text": "We have 3 salespeople and leads are coming from our website contact form, but they sit in Gmail for days. We tried HubSpot but nobody updates it. We need someone to fix this automatically.",
        "source": "webform",
    },
    {
        "first_name": "Sarah",
        "last_name": "Mueller",
        "email": "sarah@nextstep-growth.de",
        "company_name": "NextStep Growth",
        "inquiry_text": "How much does it cost to integrate your lead automation with Pipedrive? We get about 50 leads per month from ads and referrals and need them auto-assigned with follow-up reminders.",
        "source": "webform",
    },
    {
        "first_name": "Aleksandar",
        "last_name": "Nikolic",
        "email": "a.nikolic@techstudio.rs",
        "company_name": "TechStudio",
        "inquiry_text": "We are a software agency with no CRM at all. Everything is in spreadsheets. We want to connect our Webflow contact form and start tracking leads properly with automated first responses.",
        "source": "webform",
    },
]

async def main():
    await init_db()
    for lead in DEMO_LEADS:
        result = await process_lead(lead)
        print(f"Created: {result.lead_id} — {lead['first_name']} {lead['last_name']} / {lead['company_name']}")
    print("\nDone. Open http://localhost:8765")

asyncio.run(main())
