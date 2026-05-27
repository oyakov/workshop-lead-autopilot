from services.llm import chat

INTENT_PROMPT = """Classify the lead inquiry into exactly one category.

Categories:
- automation: wants to automate a business process (CRM, docs, emails, workflows)
- integration: wants to connect existing tools/systems
- pricing: asking about cost or plans
- partnership: wants to collaborate or white-label
- other: anything else

Reply with ONLY the category word, nothing else.

Inquiry: {inquiry}"""


async def classify_intent(inquiry_text: str) -> str:
    try:
        result = await chat(
            [{"role": "user", "content": INTENT_PROMPT.format(inquiry=inquiry_text[:500])}],
            max_tokens=10
        )
        result = result.strip().lower().split()[0] if result.strip() else "other"
        valid = {"automation", "integration", "pricing", "partnership", "other"}
        return result if result in valid else "other"
    except Exception:
        return "other"
