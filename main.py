import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from models import LeadIn
from services import db
from services.pipeline import process_lead, approve_draft, check_stale_leads

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    scheduler.add_job(check_stale_leads, "interval", minutes=5)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Lead-to-CRM Autopilot", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=FileResponse)
async def root():
    return FileResponse("static/index.html")


@app.post("/api/leads")
async def intake_lead(lead_in: LeadIn):
    lead = await process_lead(lead_in.model_dump())
    return {"lead_id": lead.lead_id, "status": "processing", "owner": lead.owner}


@app.get("/api/leads")
async def get_leads():
    return await db.list_leads()


@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: str):
    lead = await db.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@app.get("/api/leads/{lead_id}/events")
async def get_lead_events(lead_id: str):
    return await db.get_events(lead_id)


@app.post("/api/leads/{lead_id}/approve")
async def approve_lead_draft(lead_id: str):
    ok = await approve_draft(lead_id)
    if not ok:
        raise HTTPException(400, "Cannot approve: lead not found or already approved")
    return {"ok": True}


@app.post("/api/leads/{lead_id}/sla-check")
async def manual_sla_check(lead_id: str):
    """Demo helper: manually trigger SLA breach for a lead."""
    from datetime import datetime
    from services.pipeline import _log
    await db.update_lead(lead_id, {"next_action_due_at": "2000-01-01T00:00:00"})
    await check_stale_leads()
    return {"ok": True}
