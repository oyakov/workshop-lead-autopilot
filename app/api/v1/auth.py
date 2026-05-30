"""
Authentication router — handles login and logout endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.services.auth import sign_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(credentials: LoginRequest, response: Response):
    """Log in user and set HttpOnly session cookie."""
    cfg = get_settings()
    
    # Secure credential matching
    if credentials.username != cfg.admin_username or credentials.password != cfg.admin_password:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    # Generate signed token
    token = sign_token(credentials.username, cfg.secret_key)
    
    # Set HttpOnly session cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=cfg.environment == "production",  # Only require HTTPS in production
        max_age=86400 * 7,  # 7 days
    )
    
    return {"ok": True, "username": credentials.username}


@router.post("/logout")
async def logout(response: Response):
    """Log out user and clear HttpOnly cookie."""
    response.delete_cookie(
        key="session_token",
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}
