"""Health check endpoint."""
from fastapi import APIRouter
from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health():
    cfg = get_settings()
    return {
        "status": "ok",
        "agency": cfg.agency_name,
        "crm": cfg.crm_provider,
        "llm": cfg.llm_provider,
        "imap": cfg.imap_enabled,
        "scoring": cfg.scoring_enabled,
        "followup_auto": cfg.followup_auto_send,
    }
