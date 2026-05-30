"""
Central configuration via pydantic-settings.
All values read from environment / .env file.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    agency_name: str = "Workshop"
    environment: Literal["development", "production"] = "development"
    secret_key: str = "change-me-in-production"
    admin_username: str = "admin"
    admin_password: str = "vestint-secure-autopilot-2026"
    webhook_token: str = "n8n_secret_token_change_me"

    # ── Supabase ─────────────────────────────────────────
    supabase_url: str = ""
    supabase_key: str = ""   # service_role key

    # ── LLM Primary ──────────────────────────────────────
    llm_provider: Literal["gemini", "lmstudio", "openai"] = "lmstudio"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-lite"

    # ── LLM Fallback ─────────────────────────────────────
    llm_fallback_provider: str = ""   # "" = disabled
    llm_base_url: str = "http://localhost:1234/v1"
    llm_api_key: str = "lm-studio"
    llm_model: str = "google/gemma-3-4b"

    # ── CRM ──────────────────────────────────────────────
    crm_provider: Literal["hubspot", "pipedrive", "amocrm", "none"] = "hubspot"
    hubspot_token: str = ""
    pipedrive_api_key: str = ""
    pipedrive_company_domain: str = ""
    amocrm_subdomain: str = ""
    amocrm_token: str = ""

    # ── Email Intake (IMAP) ───────────────────────────────
    imap_enabled: bool = False
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"
    imap_poll_interval_seconds: int = 60

    # ── Email Sending (SMTP) ──────────────────────────────
    smtp_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # ── Follow-up ─────────────────────────────────────────
    followup_auto_send: bool = True
    sla_hours: int = 24
    followup_client_hours: int = 48
    followup_final_hours: int = 72   # T+72h: 3rd and final touch

    # ── Outreach ──────────────────────────────────────────
    calendar_link: str = ""          # e.g. https://cal.com/yourname/15min

    # ── Telegram ─────────────────────────────────────────
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_ids: str = ""   # comma-separated

    @property
    def telegram_chat_id_list(self) -> list[int]:
        if not self.telegram_chat_ids:
            return []
        return [int(cid.strip()) for cid in self.telegram_chat_ids.split(",") if cid.strip()]

    # ── Owners ───────────────────────────────────────────
    owners: str = "oleg@workshop.ai"   # comma-separated

    @property
    def owner_list(self) -> list[str]:
        return [o.strip() for o in self.owners.split(",") if o.strip()]

    # ── n8n ──────────────────────────────────────────────
    n8n_webhook_base_url: str = "http://n8n:5678"
    n8n_user: str = "admin"
    n8n_password: str = "changeme"

    # ── Scoring ───────────────────────────────────────────
    scoring_enabled: bool = True
    score_hot_threshold: int = 70
    score_warm_threshold: int = 40


    @model_validator(mode="after")
    def _warn_insecure_defaults(self) -> "Settings":
        _INSECURE = {"change-me-in-production", "changeme"}
        if self.environment == "production":
            if self.secret_key in _INSECURE:
                raise ValueError("SECRET_KEY must be set to a strong random value in production.")
            if self.webhook_token in {"n8n_secret_token_change_me"}:
                raise ValueError("WEBHOOK_TOKEN must be changed from the default in production.")
        else:
            if self.secret_key in _INSECURE:
                logger.warning(
                    "SECRET_KEY is using an insecure default. "
                    "Set SECRET_KEY env var before deploying to production."
                )
            if self.webhook_token in {"n8n_secret_token_change_me"}:
                logger.warning(
                    "WEBHOOK_TOKEN is using an insecure default. "
                    "Set WEBHOOK_TOKEN env var before deploying to production."
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
