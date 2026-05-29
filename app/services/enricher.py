"""
Lead enricher — intent classification + LLM-based scoring.
"""
from __future__ import annotations

import json
import logging
import re

from app.llm import gateway as llm
from app.llm.prompts import INTENT_CLASSIFICATION, LEAD_SCORING

logger = logging.getLogger(__name__)

VALID_INTENTS = {"automation", "integration", "pricing", "partnership", "other"}


async def classify_intent(inquiry_text: str) -> str:
    """Classify lead intent into one of the predefined categories."""
    try:
        result = await llm.chat(
            [{"role": "user", "content": INTENT_CLASSIFICATION.format(inquiry=inquiry_text[:500])}],
            max_tokens=10,
        )
        word = result.strip().lower().split()[0] if result.strip() else "other"
        return word if word in VALID_INTENTS else "other"
    except Exception as e:
        logger.warning("Intent classification failed: %s", e)
        return "other"


async def score_lead(lead: dict) -> tuple[int, str, str]:
    """
    Score lead 0–100 and return (score, label, reason).
    Uses LLM; falls back to rule-based scoring if LLM fails.
    """
    try:
        prompt = LEAD_SCORING.format(
            first_name=lead.get("first_name", ""),
            last_name=lead.get("last_name", ""),
            email=lead.get("email", ""),
            company_name=lead.get("company_name", ""),
            company_domain=lead.get("company_domain", ""),
            inquiry_text=lead.get("inquiry_text", "")[:400],
            intent_category=lead.get("intent_category", "other"),
        )
        raw = await llm.chat(
            [{"role": "user", "content": prompt}],
            max_tokens=150,
        )

        # Extract JSON from response
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            score = max(0, min(100, int(data.get("score", 0))))
            label = data.get("label", "cold")
            if label not in ("hot", "warm", "cold"):
                label = _score_to_label(score)
            reason = data.get("reason", "")
            return score, label, reason

    except Exception as e:
        logger.warning("LLM scoring failed, using rule-based fallback: %s", e)

    # Rule-based fallback
    return _rule_based_score(lead)


def _score_to_label(score: int) -> str:
    from app.config import get_settings
    cfg = get_settings()
    if score >= cfg.score_hot_threshold:
        return "hot"
    if score >= cfg.score_warm_threshold:
        return "warm"
    return "cold"


def _rule_based_score(lead: dict) -> tuple[int, str, str]:
    """Simple heuristic scoring when LLM is unavailable."""
    score = 30  # baseline
    reasons = []

    if lead.get("company_domain"):
        score += 15
        reasons.append("business email")
    if len(lead.get("inquiry_text", "")) > 100:
        score += 15
        reasons.append("detailed inquiry")
    if lead.get("company_name"):
        score += 10
        reasons.append("company identified")
    if lead.get("phone"):
        score += 10
        reasons.append("phone provided")
    if lead.get("intent_category") in ("automation", "integration"):
        score += 10
        reasons.append(f"intent={lead['intent_category']}")

    score = min(score, 100)
    label = _score_to_label(score)
    reason = "Rule-based: " + ", ".join(reasons) if reasons else "Baseline score"
    return score, label, reason
