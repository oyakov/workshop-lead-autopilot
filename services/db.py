import aiosqlite
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "leads.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                lead_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def save_lead(lead: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO leads (lead_id, data, created_at) VALUES (?, ?, ?)",
            (lead["lead_id"], json.dumps(lead, ensure_ascii=False), lead["created_at"])
        )
        await db.commit()


async def get_lead(lead_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT data FROM leads WHERE lead_id = ?", (lead_id,)) as cur:
            row = await cur.fetchone()
            return json.loads(row[0]) if row else None


async def list_leads() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT data FROM leads ORDER BY created_at DESC") as cur:
            rows = await cur.fetchall()
            return [json.loads(r[0]) for r in rows]


async def update_lead(lead_id: str, updates: dict):
    lead = await get_lead(lead_id)
    if not lead:
        return
    lead.update(updates)
    await save_lead(lead)


async def log_event(event: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO events (event_id, lead_id, event_type, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (event["event_id"], event["lead_id"], event["event_type"], event.get("detail", ""), event["created_at"])
        )
        await db.commit()


async def get_events(lead_id: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT event_id, lead_id, event_type, detail, created_at FROM events WHERE lead_id = ? ORDER BY created_at",
            (lead_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [{"event_id": r[0], "lead_id": r[1], "event_type": r[2], "detail": r[3], "created_at": r[4]} for r in rows]
