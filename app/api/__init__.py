"""API v1 router assembly."""
from fastapi import APIRouter

from app.api.v1 import health, leads, webhooks, auth

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth.router)
v1_router.include_router(health.router)
v1_router.include_router(leads.router)
v1_router.include_router(webhooks.router)
