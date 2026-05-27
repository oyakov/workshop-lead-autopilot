import re


def extract_domain(email: str) -> str:
    match = re.search(r"@([\w.-]+)", email)
    if not match:
        return ""
    domain = match.group(1).lower()
    free = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "mail.ru", "yandex.ru", "icloud.com"}
    return "" if domain in free else domain


def normalize_phone(phone: str) -> str:
    return re.sub(r"[^\d+]", "", phone)


def normalize_name(name: str) -> tuple[str, str]:
    parts = name.strip().split()
    if len(parts) >= 2:
        return parts[0].capitalize(), " ".join(parts[1:]).capitalize()
    return parts[0].capitalize() if parts else "", ""


def normalize_lead(raw: dict) -> dict:
    lead = dict(raw)
    lead["email"] = lead.get("email", "").strip().lower()
    lead["company_domain"] = extract_domain(lead["email"])
    if not lead.get("company_name") and lead["company_domain"]:
        lead["company_name"] = lead["company_domain"].split(".")[0].capitalize()
    lead["phone"] = normalize_phone(lead.get("phone", ""))
    lead["first_name"] = lead.get("first_name", "").strip().capitalize()
    lead["last_name"] = lead.get("last_name", "").strip().capitalize()
    return lead


OWNERS = ["oleg@workshop.ai", "boris@workshop.ai"]
_round_robin = [0]


def assign_owner() -> str:
    idx = _round_robin[0] % len(OWNERS)
    _round_robin[0] += 1
    return OWNERS[idx]
