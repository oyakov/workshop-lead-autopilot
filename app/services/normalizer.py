"""Lead normalizer — cleans and standardises raw lead fields."""
from __future__ import annotations

import re
import logging

import tldextract

logger = logging.getLogger(__name__)

FREE_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "mail.ru", "yandex.ru", "icloud.com", "protonmail.com",
    "aol.com", "live.com", "msn.com", "me.com",
}


def extract_domain(email: str) -> str:
    m = re.search(r"@([\w.-]+)", email)
    if not m:
        return ""
    domain = m.group(1).lower()
    if domain in FREE_DOMAINS:
        return ""
    # Validate it looks like a real domain
    ext = tldextract.extract(domain)
    if not ext.domain or not ext.suffix:
        return ""
    return domain


def normalize_phone(phone: str) -> str:
    return re.sub(r"[^\d+]", "", phone)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_lead(raw: dict) -> dict:
    """Return a cleaned copy of the raw lead dict."""
    lead = dict(raw)

    # Email
    lead["email"] = normalize_email(lead.get("email", ""))

    # Company domain from email
    domain = extract_domain(lead["email"])
    lead["company_domain"] = domain

    # Infer company name from domain if missing
    if not lead.get("company_name") and domain:
        ext = tldextract.extract(domain)
        lead["company_name"] = ext.domain.capitalize()

    # Phone
    lead["phone"] = normalize_phone(lead.get("phone", ""))

    # Names
    lead["first_name"] = lead.get("first_name", "").strip().capitalize()
    lead["last_name"] = lead.get("last_name", "").strip().capitalize()

    # Trim inquiry
    lead["inquiry_text"] = lead.get("inquiry_text", "").strip()

    return lead
