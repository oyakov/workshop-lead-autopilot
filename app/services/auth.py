"""
Cryptographic session signature and verification helpers.
Implements hmac SHA-256 signed session tokens with zero dependencies.
"""
from __future__ import annotations

import base64
import hmac
import hashlib
import json
import logging
import time
from fastapi import Request, HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)


def sign_token(username: str, secret: str, expires_in_seconds: int = 86400 * 7) -> str:
    """
    Generate a cryptographically-signed session token.
    Payload: {"username": str, "expires": int}
    """
    expires = int(time.time()) + expires_in_seconds
    payload = json.dumps({"username": username, "expires": expires})
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    
    # Sign using HMAC SHA-256
    sig = hmac.new(
        secret.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload_b64}.{sig}"


def verify_token(token: str, secret: str) -> str | None:
    """
    Verify signature and expiration of a session token.
    Returns username if valid, otherwise None.
    """
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        
        payload_b64, signature = parts
        
        # Verify HMAC signature in constant time to prevent timing attacks
        expected_sig = hmac.new(
            secret.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
        
        # Pad base64 string
        missing_padding = len(payload_b64) % 4
        if missing_padding:
            payload_b64 += "=" * (4 - missing_padding)
            
        # Decode and load payload
        payload_data = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_data)
        
        # Check expiration
        if time.time() > payload["expires"]:
            logger.warning("Session token has expired")
            return None
            
        return payload["username"]
    except Exception as e:
        logger.error("Token verification failed: %s", e)
        return None


async def verify_session(request: Request) -> str:
    """
    FastAPI dependency injection to verify the session_token HTTP-only cookie.
    Raises 401 Unauthorized if invalid or missing.
    """
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication cookie missing")
        
    cfg = get_settings()
    username = verify_token(token, cfg.secret_key)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
        
    return username
