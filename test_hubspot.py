import asyncio, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from services.hubspot import create_deal

async def main():
    lead = {
        "first_name": "Marko",
        "last_name": "Jovanovic",
        "email": "marko@delta-consulting.rs",
        "company_name": "Delta Consulting",
        "company_domain": "delta-consulting.rs",
        "inquiry_text": "We have 3 salespeople and leads sit in Gmail for days. We need this automated.",
    }
    print("Creating deal...")
    deal_id = await create_deal(lead)
    if deal_id:
        print(f"SUCCESS — Deal ID: {deal_id}")
        print(f"Open: https://app-eu1.hubspot.com/contacts/148571733/deal/{deal_id}")
    else:
        print("FAILED")

asyncio.run(main())
