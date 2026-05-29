-- =============================================================
-- Migration 001: Initial schema for Lead-to-CRM Autopilot
-- Run in Supabase SQL Editor or via supabase CLI
-- =============================================================

-- ── LEADS ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
    lead_id             TEXT PRIMARY KEY,
    source              TEXT NOT NULL DEFAULT 'webform',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Contact
    first_name          TEXT,
    last_name           TEXT,
    email               TEXT NOT NULL,
    phone               TEXT,

    -- Company
    company_name        TEXT,
    company_domain      TEXT,
    country             TEXT,
    timezone            TEXT,

    -- Lead details
    inquiry_text        TEXT,
    intent_category     TEXT DEFAULT 'other'
                        CHECK (intent_category IN ('automation','integration','pricing','partnership','other')),

    -- Scoring (v1)
    score               SMALLINT DEFAULT 0,
    score_label         TEXT DEFAULT 'unknown'
                        CHECK (score_label IN ('hot','warm','cold','unknown')),
    score_reason        TEXT,

    -- Ownership
    owner               TEXT,
    status              TEXT NOT NULL DEFAULT 'new'
                        CHECK (status IN ('new','contacted','qualified','meeting_set','closed_won','closed_lost')),

    -- CRM references
    crm_contact_id      TEXT,
    crm_company_id      TEXT,
    crm_deal_id         TEXT,

    -- Timeline
    last_action_at      TIMESTAMPTZ,
    next_action_due_at  TIMESTAMPTZ,

    -- Draft email
    draft_subject       TEXT,
    draft_body          TEXT,
    draft_approved      BOOLEAN DEFAULT false,
    draft_sent          BOOLEAN DEFAULT false,

    -- Follow-up
    followup_count      SMALLINT DEFAULT 0,
    followup_last_at    TIMESTAMPTZ
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS leads_updated_at ON leads;
CREATE TRIGGER leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads(company_domain);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_owner ON leads(owner);
CREATE INDEX IF NOT EXISTS idx_leads_due ON leads(next_action_due_at) WHERE status IN ('new','contacted');

-- ── EVENTS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    event_id    TEXT PRIMARY KEY,
    lead_id     TEXT NOT NULL REFERENCES leads(lead_id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL,
    detail      JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_lead ON events(lead_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);

-- ── TEMPLATES ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS templates (
    template_id     TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name            TEXT NOT NULL,
    intent_category TEXT DEFAULT '',   -- empty = applies to all
    subject_tpl     TEXT NOT NULL,
    body_tpl        TEXT NOT NULL,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Seed default template
INSERT INTO templates (name, intent_category, subject_tpl, body_tpl)
VALUES (
    'Default Reply',
    '',
    'Re: Your inquiry - {{ first_name }}',
    'Hi {{ first_name }},

Thanks for reaching out! We specialise in AI automation and can definitely help with what you described.

Would you be open to a quick 15-min discovery call this week? Here is my calendar: [CALENDAR_LINK]

Best,
The {{ agency_name }} Team'
)
ON CONFLICT DO NOTHING;

-- ── ROW LEVEL SECURITY ────────────────────────────────────────
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS (used by server-side app)
-- For anon/authenticated access, add specific policies as needed
