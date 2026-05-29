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
        "supabase": "connected" if (cfg.supabase_url and cfg.supabase_key) else "local_fallback",
        "crm": cfg.crm_provider,
        "primary_llm": cfg.llm_provider,
        "gemini": bool(cfg.gemini_api_key),
        "fallback_llm": cfg.llm_fallback_provider or "none",
        "imap": cfg.imap_enabled,
        "smtp": cfg.smtp_enabled,
        "telegram": cfg.telegram_enabled,
        "scoring": cfg.scoring_enabled,
        "followup_auto": cfg.followup_auto_send,
    }
