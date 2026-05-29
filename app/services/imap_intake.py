"""
IMAP email intake service.
Polls mailbox, parses incoming emails into leads.
Runs as background task via APScheduler.
"""
from __future__ import annotations

import asyncio
import email
import logging
import re
from datetime import datetime, timezone
from email.header import decode_header

from app.config import get_settings
from app.models.lead import LeadIn

logger = logging.getLogger(__name__)


def _decode_header_value(value: str) -> str:
    """Decode RFC 2047 encoded email headers."""
    try:
        parts = decode_header(value)
        decoded = []
        for part, enc in parts:
            if isinstance(part, bytes):
                decoded.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                decoded.append(part)
        return "".join(decoded)
    except Exception:
        return value or ""


def _extract_email_address(header: str) -> tuple[str, str]:
    """Extract (name, email) from 'Name <email>' format."""
    match = re.search(r"<([^>]+)>", header)
    if match:
        email_addr = match.group(1).strip()
        name = header[:header.index("<")].strip().strip('"')
        name = _decode_header_value(name)
    else:
        email_addr = header.strip()
        name = ""
    return name, email_addr


def _get_body(msg: email.message.Message) -> str:
    """Extract plain text body from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                try:
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                except Exception:
                    body = str(part.get_payload())
                break
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            body = str(msg.get_payload())
    return body.strip()[:2000]


async def poll_inbox() -> list[LeadIn]:
    """
    Connect to IMAP, fetch UNSEEN emails, mark as SEEN, return LeadIn list.
    Returns empty list if IMAP is disabled or connection fails.
    """
    cfg = get_settings()
    if not cfg.imap_enabled:
        return []

    leads: list[LeadIn] = []

    try:
        import aioimaplib
        client = aioimaplib.IMAP4_SSL(cfg.imap_host, cfg.imap_port)
        await client.wait_hello_from_server()
        await client.login(cfg.imap_user, cfg.imap_password)
        await client.select(cfg.imap_folder)

        _, data = await client.search("UNSEEN")
        if not data or not data[0]:
            await client.logout()
            return []

        msg_ids = data[0].decode().split()
        logger.info("IMAP: found %d unseen messages", len(msg_ids))

        for msg_id in msg_ids[-50:]:  # process max 50 at a time
            try:
                _, msg_data = await client.fetch(msg_id, "(RFC822)")
                raw = msg_data[1]
                if isinstance(raw, (bytes, bytearray)):
                    msg = email.message_from_bytes(raw)
                else:
                    continue

                from_header = _decode_header_value(msg.get("From", ""))
                subject = _decode_header_value(msg.get("Subject", ""))
                name, from_email = _extract_email_address(from_header)
                body = _get_body(msg)

                if not from_email or "@" not in from_email:
                    continue

                # Parse name parts
                name_parts = name.strip().split(maxsplit=1)
                first = name_parts[0] if name_parts else ""
                last = name_parts[1] if len(name_parts) > 1 else ""

                inquiry = f"[Subject: {subject}]\n\n{body}" if subject else body

                leads.append(LeadIn(
                    first_name=first,
                    last_name=last,
                    email=from_email,
                    inquiry_text=inquiry[:1500],
                    source="email_imap",
                ))

                # Mark as seen
                await client.store(msg_id, "+FLAGS", "\\Seen")

            except Exception as e:
                logger.error("IMAP: failed to parse message %s: %s", msg_id, e)

        await client.logout()

    except Exception as e:
        logger.error("IMAP polling error: %s", e)

    return leads


async def run_imap_intake() -> None:
    """Called by scheduler. Polls IMAP and submits leads to pipeline."""
    from app.services.pipeline import process_lead
    leads = await poll_inbox()
    for lead_in in leads:
        try:
            await process_lead(lead_in.model_dump())
        except Exception as e:
            logger.error("Failed to process IMAP lead %s: %s", lead_in.email, e)
