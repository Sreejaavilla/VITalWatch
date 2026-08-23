"""Database access — SQLite on disk, or PostgreSQL (Supabase) in the cloud.

One connection API, two drivers. `DATABASE_URL` decides: set it and every query runs
against Postgres; leave it unset and the same queries run against a local SQLite file.
Nothing above this module knows which, and no query is written twice.

That switch is the point rather than a convenience. The demo's central claim is an audit
chain that cannot be altered, and a chain that only holds on one engine is a weaker
claim than one that holds on both — the head hash after seeding is identical either way,
which is a thing you can show rather than assert. It is also the stage insurance: if the
venue network dies, `unset DATABASE_URL` and the whole system runs from a file.

**Two deliberate choices about column types.** Dates are `TEXT` holding ISO-8601, and
booleans are `INTEGER` holding 0/1, on Postgres exactly as on SQLite. Both are
unidiomatic for Postgres. Both are kept because the audit payload is the canonical JSON
of a row, and changing how a value round-trips would change the payload, which would
change every hash after it. ISO-8601 text sorts and compares correctly, so nothing is
lost but idiom. The cast to a real `date` happens in the one place that needs date
arithmetic — see `days_between`.

The append-only guarantee is enforced at the storage layer on both engines: SQLite gets
`RAISE(ABORT)` triggers, Postgres gets a `RAISE EXCEPTION` trigger function, and on
Postgres the tables additionally carry row-level security so the project's auto-generated
REST API cannot read them.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Union

from .config import settings

# --------------------------------------------------------------------------- schema

#: Table DDL, shared by both engines. `{float}` is the one type that differs: SQLite's
#: REAL is 8-byte, Postgres' REAL is 4-byte and would render a coding confidence of
#: 0.884 as 0.8840000033378601 on screen.
_TABLES = """
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
    coding_confidence   {float},
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

-- An investigator's decision on an investigation case. Ordinary, mutable data: the
-- decision itself is the record, and its immutable copy lives in audit_events, written
-- in the same transaction. Two tables because they answer different questions — this
-- one "what is the current disposition", that one "what was decided, by whom, when".
CREATE TABLE IF NOT EXISTS investigation_decisions (
    id             TEXT PRIMARY KEY,
    case_id        TEXT NOT NULL,
    study_id       TEXT NOT NULL REFERENCES studies(id),
    action         TEXT NOT NULL,
    reason         TEXT NOT NULL,
    actor          TEXT NOT NULL,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    decided_at     TEXT NOT NULL
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
"""

_INDEXES = """
CREATE INDEX IF NOT EXISTS ix_subjects_study        ON subjects(study_id);
CREATE INDEX IF NOT EXISTS ix_visits_study          ON visits(study_id);
CREATE INDEX IF NOT EXISTS ix_queries_study         ON queries(study_id);
CREATE INDEX IF NOT EXISTS ix_deviations_study      ON deviations(study_id);
CREATE INDEX IF NOT EXISTS ix_adverse_events_study  ON adverse_events(study_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_seq      ON audit_events(seq);
CREATE INDEX IF NOT EXISTS ix_inv_decisions_case    ON investigation_decisions(case_id);
"""

#: The immutability guarantee, at the storage layer rather than the application layer.
_TRIGGERS_SQLITE = """
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
"""

#: The same guarantee in Postgres. `TG_OP` makes one function serve both triggers and
#: name the operation it refused, so the error a tamperer sees is as specific as SQLite's.
#: Postgres has no CREATE TRIGGER IF NOT EXISTS, hence the DROP first.
_TRIGGERS_POSTGRES = """
CREATE OR REPLACE FUNCTION audit_events_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_events is append-only: % is not permitted', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events;
CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events
FOR EACH ROW EXECUTE FUNCTION audit_events_append_only();

DROP TRIGGER IF EXISTS audit_events_no_delete ON audit_events;
CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION audit_events_append_only();
"""

#: Tables the seed check counts against. study_sites is a join table, not portfolio data.
SEEDED_TABLES = (
    "studies", "sites", "subjects", "visits", "deviations",
    "queries", "adverse_events", "milestones", "alerts", "investigation_decisions",
    "audit_events",
)

#: Every table, for the RLS pass below.
_ALL_TABLES = SEEDED_TABLES + ("study_sites",)

#: Deny-all row-level security. A Supabase project publishes a REST API over its tables
#: to the `anon` key that ships in client code; with RLS on and no policy written, that
#: API returns nothing. The application is unaffected because it connects as the table
#: owner over Postgres directly, and owners bypass RLS. Synthetic data or not, an
#: openly readable clinical schema is not a thing to leave lying around.
_RLS_POSTGRES = "\n".join(
    f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;" for t in _ALL_TABLES
)

#: Kept under its original name: this is the SQLite schema, unchanged in content.
SCHEMA = _TABLES.format(float="REAL") + _TRIGGERS_SQLITE + _INDEXES
SCHEMA_POSTGRES = (
    _TABLES.format(float="DOUBLE PRECISION")
    + _TRIGGERS_POSTGRES
    + _INDEXES
    + _RLS_POSTGRES
)


# --------------------------------------------------------------------- driver choice


def is_postgres() -> bool:
    """True when `DATABASE_URL` is set. The single switch for everything below."""
    return bool(settings.database_url)


def backend() -> str:
    """`"postgres"` or `"sqlite"` — for /health, so the running engine is visible."""
    return "postgres" if is_postgres() else "sqlite"


def days_between(later: str, earlier: str) -> str:
    """SQL fragment: whole days between two ISO-8601 date expressions.

    The one place the TEXT-dates decision has to be paid for. SQLite reads them with
    `julianday`; Postgres casts to `date` and subtracts, which yields an integer
    directly. Both arguments are interpolated as SQL, so pass column names or `?`.
    """
    if is_postgres():
        return f"(CAST({later} AS date) - CAST({earlier} AS date))"
    return f"CAST(julianday({later}) - julianday({earlier}) AS INTEGER)"


# ------------------------------------------------------------------ postgres driver


class Row(dict):
    """A result row addressable by name or by position.

    `sqlite3.Row` supports both, and the query code above relies on both — `row["id"]`
    when reading a record, `row[0]` when pulling a single count out. psycopg's own row
    factories give one or the other, so this gives both and the callers stay unchanged.
    """

    def __init__(self, pairs: Iterable[tuple[str, Any]]):
        super().__init__(pairs)
        self._positional = tuple(self.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._positional[key]
        return super().__getitem__(key)

    def __iter__(self):
        """Iterate values, as `sqlite3.Row` does — not keys, as a dict would.

        Without this, `a, b = row` unpacks column *names* on Postgres and column
        *values* on SQLite: the same statement quietly meaning two different things,
        which is the worst kind of portability bug because nothing raises. `dict(row)`
        is unaffected — it goes through `keys()`.
        """
        return iter(self._positional)


def _row_factory(cursor):
    columns = [c.name for c in cursor.description or ()]

    def build(values):
        return Row(zip(columns, values))

    return build


#: Named placeholders, `:study_id`, but never a `::` cast. The negative lookbehind and
#: lookahead keep this from touching Postgres cast syntax if any is ever written here.
_NAMED = re.compile(r"(?<!:):([a-zA-Z_]\w*)")


def _to_pg(sql: str) -> str:
    """Rewrite SQLite placeholders for psycopg.

    Both styles the codebase uses are translated: positional `?` becomes `%s`, and named
    `:study_id` becomes `%(study_id)s`. Literal `%` is doubled first so psycopg does not
    read it as a placeholder of its own.

    This is string substitution, which is safe here only because no query in this
    codebase contains a `?`, a `%` or a `:word` inside a string literal — checked, and
    worth re-checking before adding one.
    """
    return _NAMED.sub(r"%(\1)s", sql.replace("%", "%%")).replace("?", "%s")


class PostgresConnection:
    """A psycopg connection wearing the `sqlite3.Connection` API this codebase uses.

    Only the surface actually called is implemented: execute, executescript, commit,
    rollback, close. Transaction semantics match SQLite's — psycopg opens a transaction
    on first statement and holds it until `commit()`, so a route that writes a record and
    its audit row in sequence still commits both together or neither.
    """

    def __init__(self, raw, release=None):
        self._raw = raw
        self._release = release

    def execute(self, sql: str, params: Any = ()):
        cursor = self._raw.cursor(row_factory=_row_factory)
        # A mapping goes through untouched — it pairs with the `%(name)s` form and
        # tuple() on a dict would silently hand psycopg the keys.
        cursor.execute(_to_pg(sql), params if isinstance(params, Mapping) else tuple(params))
        return cursor

    def executescript(self, script: str) -> None:
        # No parameters, so psycopg does no interpolation and the `%` inside the
        # trigger's RAISE EXCEPTION survives untouched.
        with self._raw.cursor() as cursor:
            cursor.execute(script)

    def pipeline(self):
        """psycopg pipeline mode: send many statements without waiting for each reply."""
        return self._raw.pipeline()

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        if self._release is not None:
            self._release(self._raw)
        else:
            self._raw.close()

    @property
    def raw(self):
        return self._raw


Connection = Union[sqlite3.Connection, PostgresConnection]


def _dsn() -> str:
    """The connection string, with TLS required if the URL did not already say so."""
    url = settings.database_url or ""
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def _connect_kwargs() -> dict:
    return {
        # Server-side prepared statements break under a transaction-mode pooler, which
        # is what Supabase hands out on port 6543. Disabling them costs little at this
        # query volume and makes either pooler port work.
        "prepare_threshold": None,
        # Fail fast. A demo that hangs is worse than a demo that says it cannot connect.
        "connect_timeout": settings.db_connect_timeout,
        "application_name": settings.app_name,
    }


_pool = None


def _get_pool():
    """Lazily built connection pool, shared by every request.

    Supabase is a network hop away and TLS handshakes are not free; without a pool every
    page load would pay one. Built on first use rather than at import so that scripts
    and tests that never touch Postgres never open a socket.
    """
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(
            _dsn(),
            min_size=1,
            max_size=settings.db_pool_max,
            kwargs=_connect_kwargs(),
            open=True,
        )
    return _pool


def close_pool() -> None:
    """Shut the pool down on application exit. Safe to call when there is no pool."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


# ------------------------------------------------------------------------ public API


def connect(db_path: Path | None = None) -> Connection:
    """Open a standalone connection.

    Used by scripts and by startup. Requests use `get_db`, which pools instead.
    `db_path` applies to SQLite only and is ignored when `DATABASE_URL` is set.
    """
    if is_postgres():
        import psycopg

        return PostgresConnection(psycopg.connect(_dsn(), **_connect_kwargs()))

    path = Path(db_path or settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False because FastAPI serves from a threadpool; every caller
    # uses a short-lived connection, so there is no shared cursor.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """FastAPI dependency. One connection per request, always released.

    On Postgres the connection goes back to the pool rather than being closed, and the
    pool rolls back anything uncommitted on the way in — so a request that read without
    committing cannot leave a transaction open behind it.
    """
    if is_postgres():
        pool = _get_pool()
        raw = pool.getconn()
        conn = PostgresConnection(raw, release=pool.putconn)
    else:
        conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def init_schema(conn: Connection) -> None:
    conn.executescript(SCHEMA_POSTGRES if is_postgres() else SCHEMA)
    conn.commit()


def is_empty(conn: Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM studies").fetchone()[0] == 0


@contextmanager
def bulk(conn: Connection):
    """Group many small writes into as few network round trips as possible.

    The seed is roughly 2,400 single-row INSERTs. Against a local file that is
    instantaneous; against a hosted Postgres it is 2,400 sequential round trips, which at
    a measured 152 ms to Supabase is over six minutes — long enough that a platform
    health check gives up on the deployment before it finishes booting.

    Pipeline mode sends the statements without waiting for each reply, which collapses
    that to a handful of round trips. No caller changes: the block below is the only
    thing that knows this is happening. A no-op on SQLite, which has no round trips.
    """
    if isinstance(conn, PostgresConnection):
        with conn.pipeline():
            yield
    else:
        yield


def init(seed: bool = True) -> Connection:
    """Create the schema and seed if the database has no studies.

    Called on app startup. Idempotent: an already-populated database is left alone, so a
    Supabase instance is seeded once by whichever process gets there first and every
    later boot finds it populated.
    """
    conn = connect()
    init_schema(conn)
    if seed and is_empty(conn):
        from . import datagen  # imported late — datagen imports models, not db

        with bulk(conn):
            datagen.seed(conn)
    return conn


def drop_audit_guard(conn: Connection) -> None:
    """Remove the UPDATE trigger on `audit_events`. For the tamper demonstration only.

    Kept here so the demo says the same thing on both engines: the guard is at the
    storage layer, and getting past it means dropping it deliberately with owner rights
    — at which point the hash chain is what still catches you.
    """
    if is_postgres():
        conn.execute("DROP TRIGGER audit_events_no_update ON audit_events")
    else:
        conn.execute("DROP TRIGGER audit_events_no_update")


def reset(conn: Connection) -> None:
    """Drop every table. The Postgres equivalent of `rm data/ctms.db`.

    CASCADE because the tables reference each other; the trigger function goes with the
    table it is attached to.
    """
    for table in reversed(_ALL_TABLES):
        if is_postgres():
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        else:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()


if __name__ == "__main__":
    import sys

    # `--init` is accepted as a no-op: initialising is what this command does either
    # way, and it is the form written down in ROADMAP.md.
    conn = init(seed="--no-seed" not in sys.argv)
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in SEEDED_TABLES}
    print(settings.database_url and "postgres" or str(settings.db_path))
    for table, n in counts.items():
        print(f"  {table:<16} {n:>5}")
    conn.close()
