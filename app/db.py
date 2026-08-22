"""SQLite connection, schema, and startup seed.

One file, one database, no migrations. The schema is created if absent and the
database is seeded from `app.datagen` if empty — so `rm data/ctms.db` followed by a
restart is a full, deterministic reset. That is the demo-recovery plan.

The audit_events table carries UPDATE and DELETE triggers that raise. The immutability
guarantee therefore does not depend on the application behaving; it holds even against
someone with a sqlite3 shell.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS studies (
    id                     TEXT PRIMARY KEY,
    title                  TEXT NOT NULL,
    protocol_no            TEXT NOT NULL,
    ctri_number            TEXT,
    phase                  TEXT NOT NULL,
    status                 TEXT NOT NULL,
    therapeutic_area       TEXT NOT NULL,
    ec_approval_date       TEXT,
    ec_expiry_date         TEXT,
    ctri_registration_date TEXT,
    target_enrolment       INTEGER NOT NULL,
    actual_enrolment       INTEGER NOT NULL DEFAULT 0,
    pi_name                TEXT NOT NULL,
    start_date             TEXT NOT NULL,
    end_date               TEXT
);

CREATE TABLE IF NOT EXISTS sites (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    city           TEXT NOT NULL,
    state          TEXT NOT NULL,
    status         TEXT NOT NULL,
    activated_date TEXT,
    pi_name        TEXT NOT NULL,
    capacity       INTEGER NOT NULL
);

-- Many-to-many: a site runs several studies, a study runs at several sites.
CREATE TABLE IF NOT EXISTS study_sites (
    study_id TEXT NOT NULL REFERENCES studies(id),
    site_id  TEXT NOT NULL REFERENCES sites(id),
    PRIMARY KEY (study_id, site_id)
);

CREATE TABLE IF NOT EXISTS subjects (
    id              TEXT PRIMARY KEY,
    subject_code    TEXT NOT NULL UNIQUE,
    study_id        TEXT NOT NULL REFERENCES studies(id),
    site_id         TEXT NOT NULL REFERENCES sites(id),
    screened_date   TEXT NOT NULL,
    enrolled_date   TEXT,
    status          TEXT NOT NULL,
    arm             TEXT,
    age_band        TEXT,
    sex             TEXT,
    consent_version TEXT NOT NULL,
    consent_date    TEXT NOT NULL
    -- No name. No date of birth. DPDP Act 2023: see app/models.py.
);

CREATE TABLE IF NOT EXISTS visits (
    id               TEXT PRIMARY KEY,
    study_id         TEXT NOT NULL REFERENCES studies(id),
    site_id          TEXT NOT NULL REFERENCES sites(id),
    subject_code     TEXT,
    visit_name       TEXT NOT NULL,
    scheduled_date   TEXT NOT NULL,
    actual_date      TEXT,
    window_days      INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL,
    monitoring_visit INTEGER NOT NULL DEFAULT 0,
    report_filed     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS deviations (
    id            TEXT PRIMARY KEY,
    study_id      TEXT NOT NULL REFERENCES studies(id),
    site_id       TEXT NOT NULL REFERENCES sites(id),
    subject_code  TEXT,
    category      TEXT NOT NULL,
    description   TEXT NOT NULL,
    detected_date TEXT NOT NULL,
    severity      TEXT NOT NULL,
    reported_to_ec INTEGER NOT NULL DEFAULT 0,
    reported_date TEXT,
    resolution    TEXT
);

CREATE TABLE IF NOT EXISTS queries (
    id            TEXT PRIMARY KEY,
    study_id      TEXT NOT NULL REFERENCES studies(id),
    site_id       TEXT NOT NULL REFERENCES sites(id),
    subject_code  TEXT,
    field         TEXT NOT NULL,
    question      TEXT NOT NULL,
    raised_date   TEXT NOT NULL,
    raised_by     TEXT NOT NULL,
    answered_date TEXT,
    closed_date   TEXT,
    status        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS adverse_events (
    id                  TEXT PRIMARY KEY,
    study_id            TEXT NOT NULL REFERENCES studies(id),
    site_id             TEXT NOT NULL REFERENCES sites(id),
    subject_code        TEXT NOT NULL,
    narrative           TEXT NOT NULL,
    onset_date          TEXT NOT NULL,
    serious             INTEGER NOT NULL DEFAULT 0,
    severity            TEXT NOT NULL,
    causality           TEXT NOT NULL,
    outcome             TEXT NOT NULL,
    coded_term          TEXT,
    coded_code          TEXT,
    coding_confidence   REAL,
    coding_source       TEXT NOT NULL DEFAULT 'uncoded',
    suspect_drug        TEXT,
    drug_code           TEXT,
    drug_coding_source  TEXT NOT NULL DEFAULT 'uncoded',
    reported_at         TEXT NOT NULL,
    deadline_24h        TEXT,
    deadline_14d        TEXT,
    timeline_status     TEXT NOT NULL DEFAULT 'not_applicable'
);

CREATE TABLE IF NOT EXISTS milestones (
    id           TEXT PRIMARY KEY,
    study_id     TEXT NOT NULL REFERENCES studies(id),
    type         TEXT NOT NULL,
    planned_date TEXT NOT NULL,
    actual_date  TEXT,
    status       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id              TEXT PRIMARY KEY,
    rule            TEXT NOT NULL,
    severity        TEXT NOT NULL,
    study_id        TEXT NOT NULL REFERENCES studies(id),
    study_title     TEXT,
    message         TEXT NOT NULL,
    raised_at       TEXT NOT NULL,
    deep_link       TEXT NOT NULL,
    acknowledged_by TEXT,
    acknowledged_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id            TEXT PRIMARY KEY,
    seq           INTEGER NOT NULL UNIQUE,
    actor         TEXT NOT NULL,
    action        TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id   TEXT,
    before_json   TEXT,
    after_json    TEXT,
    timestamp_utc TEXT NOT NULL,
    reason        TEXT,
    prev_hash     TEXT NOT NULL,
    hash          TEXT NOT NULL
);

-- The immutability guarantee, at the storage layer rather than the application layer.
CREATE TRIGGER IF NOT EXISTS audit_events_no_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_events is append-only: UPDATE is not permitted');
END;

CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_events is append-only: DELETE is not permitted');
END;

CREATE INDEX IF NOT EXISTS ix_subjects_study        ON subjects(study_id);
CREATE INDEX IF NOT EXISTS ix_visits_study          ON visits(study_id);
CREATE INDEX IF NOT EXISTS ix_queries_study         ON queries(study_id);
CREATE INDEX IF NOT EXISTS ix_deviations_study      ON deviations(study_id);
CREATE INDEX IF NOT EXISTS ix_adverse_events_study  ON adverse_events(study_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_seq      ON audit_events(seq);
"""

#: Tables the seed check counts against. study_sites is a join table, not portfolio data.
SEEDED_TABLES = (
    "studies", "sites", "subjects", "visits", "deviations",
    "queries", "adverse_events", "milestones", "alerts", "audit_events",
)


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection with rows as mappings and foreign keys enforced.

    `check_same_thread=False` because FastAPI serves requests from a threadpool; every
    caller uses a short-lived connection from `get_db`, so there is no shared cursor.
    """
    path = Path(db_path or settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """FastAPI dependency. One connection per request, always closed."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def is_empty(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM studies").fetchone()[0] == 0


def init(seed: bool = True) -> sqlite3.Connection:
    """Create the schema and seed if the database has no studies.

    Called on app startup. Idempotent: an already-populated database is left alone.
    """
    conn = connect()
    init_schema(conn)
    if seed and is_empty(conn):
        from . import datagen  # imported late — datagen imports models, not db

        datagen.seed(conn)
    return conn


if __name__ == "__main__":
    import sys

    # `--init` is accepted as a no-op: initialising is what this command does either
    # way, and it is the form written down in ROADMAP.md.
    conn = init(seed="--no-seed" not in sys.argv)
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in SEEDED_TABLES}
    print(f"{settings.db_path}")
    for table, n in counts.items():
        print(f"  {table:<16} {n:>5}")
    conn.close()
