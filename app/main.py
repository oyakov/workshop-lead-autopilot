"""
FastAPI application entry point.

Scheduler jobs:
  - Every 60s: IMAP inbox polling (if enabled)
  - Every 15min: SLA check + Telegram alerts
  - Every hour: Follow-up processing
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api import v1_router
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()

    # ── Schedule: IMAP intake ──────────────────────────────────
    if cfg.imap_enabled:
        from app.services.imap_intake import run_imap_intake
        scheduler.add_job(
            run_imap_intake,
            "interval",
            seconds=cfg.imap_poll_interval_seconds,
            id="imap_intake",
            replace_existing=True,
        )
        logger.info("IMAP intake scheduled every %ds", cfg.imap_poll_interval_seconds)

    # ── Schedule: SLA check ────────────────────────────────────
    from app.services.sla import check_sla
    scheduler.add_job(check_sla, "interval", minutes=15, id="sla_check", replace_existing=True)

    # ── Schedule: Follow-up processing ────────────────────────
    from app.services.followup import process_followups
    scheduler.add_job(process_followups, "interval", hours=1, id="followup", replace_existing=True)

    scheduler.start()
    logger.info("Scheduler started. Jobs: %s", [j.id for j in scheduler.get_jobs()])

    yield

    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped.")


app = FastAPI(
    title="Lead-to-CRM Autopilot",
    description="B2B lead automation: Intake → Enrich → Score → CRM → Draft → Follow-up",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ────────────────────────────────────────────────
app.include_router(v1_router)

# ── Static dashboard ──────────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=FileResponse, include_in_schema=False)
async def root():
    return FileResponse("app/static/index.html")
