-- =============================================================
-- Professional-Search Diligence Schema
-- =============================================================
-- Single SQLite DB that tracks all third-party professionals the
-- user evaluates: attorneys, banks, CPAs, notaries, CAAs, insurance,
-- registered agents. Captures contacts, quotes, credentials, risks,
-- interactions, and documents.
--
-- Ported from /Users/lichenyu/accounting/scripts/diligence_schema.sql
-- with the `tasks` / `task_dependencies` tables removed (compliance-os
-- owns its own task model elsewhere).
--
-- Conventions
-- -----------
-- * `*_at` columns: ISO-8601 timestamps (UTC).
-- * `*_date` columns: date-only ISO ("YYYY-MM-DD").
-- * CHECK constraints guard soft enums; extend as new types appear.
-- =============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- -------------------------------------------------------------
-- vendors: any third-party entity evaluated
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vendors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    vendor_type     TEXT NOT NULL CHECK (vendor_type IN (
                        'attorney', 'bank', 'cpa', 'caa', 'notary',
                        'insurance', 'registered_agent', 'medical',
                        'corporate_services', 'translation',
                        'shipping', 'other'
                    )),
    category        TEXT,
    city            TEXT,
    state           TEXT,
    country         TEXT DEFAULT 'USA',
    website         TEXT,
    address         TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vendors_type     ON vendors(vendor_type);
CREATE INDEX IF NOT EXISTS idx_vendors_category ON vendors(category);

-- -------------------------------------------------------------
-- contacts: individual people at vendors
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id       INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    role            TEXT,
    email           TEXT,
    phone           TEXT,
    languages       TEXT,
    is_primary      INTEGER DEFAULT 0 CHECK (is_primary IN (0, 1)),
    notes           TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (vendor_id, name)
);

CREATE INDEX IF NOT EXISTS idx_contacts_vendor ON contacts(vendor_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email  ON contacts(email);

-- -------------------------------------------------------------
-- engagements: the user's interaction with a vendor for a purpose
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS engagements (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id           INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    purpose             TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN (
                            'prospective',
                            'inquiry_sent',
                            'in_diligence',
                            'consulted',
                            'retained',
                            'completed',
                            'declined_us',
                            'declined_them',
                            'on_hold',
                            'rejected'
                        )),
    decision_rationale  TEXT,
    first_contact_date  TEXT,
    last_contact_date   TEXT,
    next_action         TEXT,
    next_action_date    TEXT,
    score               INTEGER,
    score_max           INTEGER DEFAULT 100,
    priority            TEXT CHECK (priority IN ('low','medium','high','critical')),
    notes               TEXT,
    created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at          TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (vendor_id, purpose)
);

CREATE INDEX IF NOT EXISTS idx_engagements_vendor   ON engagements(vendor_id);
CREATE INDEX IF NOT EXISTS idx_engagements_status   ON engagements(status);
CREATE INDEX IF NOT EXISTS idx_engagements_priority ON engagements(priority);

-- -------------------------------------------------------------
-- quotes: fee quotes for specific services
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quotes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id   INTEGER NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    service         TEXT NOT NULL,
    amount_low      REAL,
    amount_high     REAL,
    currency        TEXT DEFAULT 'USD',
    quote_date      TEXT,
    is_firm         INTEGER DEFAULT 1 CHECK (is_firm IN (0, 1)),
    paid            INTEGER DEFAULT 0 CHECK (paid IN (0, 1)),
    paid_date       TEXT,
    conditions      TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quotes_engagement ON quotes(engagement_id);

-- -------------------------------------------------------------
-- evaluations: external or subjective credential ratings
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evaluations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id   INTEGER NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    criterion       TEXT NOT NULL,
    rating          TEXT,
    source          TEXT,
    weight          INTEGER DEFAULT 1,
    evaluated_date  TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_evals_engagement ON evaluations(engagement_id);

-- -------------------------------------------------------------
-- risks: risk factors per engagement (case-level or vendor-level)
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id   INTEGER NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    risk            TEXT NOT NULL,
    severity        TEXT CHECK (severity IN ('low','medium','high','critical')),
    status          TEXT DEFAULT 'open' CHECK (status IN ('open','mitigated','accepted','closed')),
    identified_date TEXT,
    mitigation      TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_risks_engagement ON risks(engagement_id);
CREATE INDEX IF NOT EXISTS idx_risks_severity   ON risks(severity);
CREATE INDEX IF NOT EXISTS idx_risks_status     ON risks(status);

-- -------------------------------------------------------------
-- interactions: emails, calls, meetings
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id   INTEGER NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
    contact_id      INTEGER REFERENCES contacts(id),
    interaction_type TEXT NOT NULL CHECK (interaction_type IN (
                        'email','phone','video','in_person','letter','sms','other'
                    )),
    direction       TEXT CHECK (direction IN ('inbound','outbound','both')),
    occurred_at     TEXT NOT NULL,
    subject         TEXT,
    summary         TEXT,
    reference_id    TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_interactions_engagement ON interactions(engagement_id);
CREATE INDEX IF NOT EXISTS idx_interactions_occurred  ON interactions(occurred_at);

-- -------------------------------------------------------------
-- documents: file references tied to a vendor or engagement
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id   INTEGER REFERENCES engagements(id) ON DELETE SET NULL,
    vendor_id       INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
    doc_type        TEXT,
    file_path       TEXT NOT NULL,
    description     TEXT,
    doc_date        TEXT,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_engagement ON documents(engagement_id);
CREATE INDEX IF NOT EXISTS idx_documents_vendor     ON documents(vendor_id);

-- =============================================================
-- updated_at triggers
-- =============================================================
CREATE TRIGGER IF NOT EXISTS trg_vendors_updated
    AFTER UPDATE ON vendors
    BEGIN UPDATE vendors SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS trg_contacts_updated
    AFTER UPDATE ON contacts
    BEGIN UPDATE contacts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS trg_engagements_updated
    AFTER UPDATE ON engagements
    BEGIN UPDATE engagements SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS trg_risks_updated
    AFTER UPDATE ON risks
    BEGIN UPDATE risks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id; END;

-- =============================================================
-- Views
-- =============================================================

-- Attorney comparison: one row per attorney engagement, with fee range +
-- open-risk count. Order by score DESC at the call site.
CREATE VIEW IF NOT EXISTS v_attorney_comparison AS
SELECT
    v.name                              AS firm,
    e.purpose,
    e.status,
    e.score,
    e.priority,
    e.next_action,
    e.next_action_date,
    e.last_contact_date,
    (SELECT MIN(amount_low) FROM quotes q WHERE q.engagement_id = e.id) AS lowest_quote,
    (SELECT MAX(amount_high) FROM quotes q WHERE q.engagement_id = e.id) AS highest_quote,
    (SELECT COUNT(*) FROM risks r WHERE r.engagement_id = e.id AND r.status = 'open') AS open_risks
FROM engagements e
JOIN vendors v ON v.id = e.vendor_id
WHERE v.vendor_type = 'attorney';

-- Generic vendor comparison (not just attorneys) — same shape, any vendor_type
CREATE VIEW IF NOT EXISTS v_vendor_comparison AS
SELECT
    v.name                              AS vendor,
    v.vendor_type,
    v.category,
    e.purpose,
    e.status,
    e.score,
    e.priority,
    e.next_action,
    e.next_action_date,
    e.last_contact_date,
    (SELECT MIN(amount_low) FROM quotes q WHERE q.engagement_id = e.id) AS lowest_quote,
    (SELECT MAX(amount_high) FROM quotes q WHERE q.engagement_id = e.id) AS highest_quote,
    (SELECT COUNT(*) FROM risks r WHERE r.engagement_id = e.id AND r.status = 'open') AS open_risks
FROM engagements e
JOIN vendors v ON v.id = e.vendor_id;

CREATE VIEW IF NOT EXISTS v_open_risks AS
SELECT
    v.name AS vendor,
    e.purpose,
    r.risk,
    r.severity,
    r.identified_date,
    r.mitigation
FROM risks r
JOIN engagements e ON e.id = r.engagement_id
JOIN vendors v ON v.id = e.vendor_id
WHERE r.status = 'open'
ORDER BY
    CASE r.severity
        WHEN 'critical' THEN 0
        WHEN 'high'     THEN 1
        WHEN 'medium'   THEN 2
        WHEN 'low'      THEN 3
        ELSE 4
    END;

CREATE VIEW IF NOT EXISTS v_vendor_directory AS
SELECT
    v.id,
    v.name,
    v.vendor_type,
    v.category,
    v.city || ', ' || COALESCE(v.state, '') AS location,
    c.name  AS primary_contact,
    c.email AS primary_email,
    c.phone AS primary_phone,
    c.languages AS languages
FROM vendors v
LEFT JOIN contacts c ON c.vendor_id = v.id AND c.is_primary = 1;
