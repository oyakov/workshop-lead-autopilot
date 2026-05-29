import asyncio, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
from services.llm import chat

async def main():
    # Test: plain text draft (no JSON)
    prompt = (
        "You are an AI agency assistant. Write a short professional reply email (3-4 sentences).\n"
        "Client: Ivan Petrov from TechCorp wrote: 'We are losing leads because our team doesn't respond fast. "
        "We use HubSpot but nobody fills it in. Can you automate our lead capture?'\n"
        "Reply as Workshop AI agency. Propose a 15-min call. Be warm and specific about their problem."
    )
    r = await chat([{"role": "user", "content": prompt}], max_tokens=300)
    print("PLAIN TEXT:", repr(r))
    print()
    print(r)

asyncio.run(main())
