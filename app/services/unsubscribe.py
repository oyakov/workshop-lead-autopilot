"""
Unsubscribe helpers.

Tokens are HMAC-SHA256 signed so recipients cannot forge tokens for
other email addresses. A valid token = proof that the email owner clicked.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)

_TOKEN_SEP = "."


def _sign(email: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).hexdigest()
    return sig


def make_unsubscribe_url(email: str, secret: str, base_url: str = "") -> str:
    """Return a signed unsubscribe URL for the given email address."""
    if not email:
        return ""
    encoded = base64.urlsafe_b64encode(email.lower().encode()).decode().rstrip("=")
    sig = _sign(email, secret)
    token = f"{encoded}{_TOKEN_SEP}{sig}"
    base = base_url.rstrip("/") if base_url else ""
    return f"{base}/api/v1/unsubscribe?token={token}"


def verify_unsubscribe_token(token: str, secret: str) -> str | None:
    """
    Verify token and return the email address, or None if invalid.
    Constant-time comparison prevents timing attacks.
    """
    try:
        parts = token.split(_TOKEN_SEP, 1)
        if len(parts) != 2:
            return None
        encoded, provided_sig = parts
        # Pad base64
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += "=" * padding
        email = base64.urlsafe_b64decode(encoded).decode()
        expected_sig = _sign(email, secret)
        if not hmac.compare_digest(provided_sig, expected_sig):
            return None
        return email
    except Exception as e:
        logger.warning("Unsubscribe token verification failed: %s", e)
        return None
