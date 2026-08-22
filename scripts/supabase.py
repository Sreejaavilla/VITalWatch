"""Drive the Supabase (Postgres) database from the command line.

    python -m scripts.supabase check     # can we connect, and what is over there
    python -m scripts.supabase init      # create the schema and seed if empty
    python -m scripts.supabase reset     # drop every table, then re-seed from scratch
    python -m scripts.supabase verify    # walk the audit chain and print the head hash

Every command reads `DATABASE_URL` from the environment or `.env`. With it unset these
operate on the local SQLite file instead, which is intentional — the same commands
should work on whichever database is configured, or "it works on Supabase" is a claim
nobody can check without editing code.

The head hash printed by `verify` is the thing worth looking at: seeded into Postgres it
is the same value as seeding into SQLite produces, because the chain hashes record
content and not storage. If those ever diverge, something about how a value round-trips
has changed and the audit trail is no longer engine-independent.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import audit, db  # noqa: E402
from app.config import settings  # noqa: E402

#: What seeding an empty database produces, on either engine. Printed alongside the
#: live value so a mismatch is visible rather than merely recorded.
EXPECTED_SEED_HEAD = "72d9d98594b990762e1115a05d5d69b6bfbe8a1bc41ef52eb923374cf3f70576"

GREEN, RED, DIM, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def _target() -> str:
    if not db.is_postgres():
        return f"sqlite · {settings.db_path}"
    # Never print the password. The host is enough to confirm you are pointed at the
    # right project, and this output tends to end up in screenshots.
    url = settings.database_url or ""
    host = url.split("@")[-1].split("/")[0] if "@" in url else "(unparsed)"
    return f"postgres · {host}"


def _counts(conn) -> dict[str, int]:
    return {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in db.SEEDED_TABLES
    }


def check() -> int:
    """Connect, report the backend and row counts, and confirm the guard is in place."""
    print(f"{DIM}target{OFF}  {_target()}")
    conn = db.connect()
    try:
        try:
            counts = _counts(conn)
        except Exception as exc:  # noqa: BLE001
            print(f"{RED}no schema yet{OFF} — run `init`. ({type(exc).__name__})")
            conn.rollback()
            return 1

        for table, n in counts.items():
            print(f"  {table:<16} {n:>5}")

        # The append-only guarantee is the one thing worth probing rather than trusting,
        # because it is enforced by DDL that a migration could quietly fail to apply.
        try:
            conn.execute("UPDATE audit_events SET actor='probe' WHERE seq=1")
            conn.rollback()
            print(f"{RED}append-only guard MISSING{OFF} — UPDATE on audit_events succeeded")
            return 1
        except Exception:  # noqa: BLE001 — refusal is the pass condition
            conn.rollback()
            print(f"{GREEN}append-only guard active{OFF} — UPDATE on audit_events refused")
        return 0
    finally:
        conn.close()


def init() -> int:
    conn = db.init(seed=True)
    print(f"{DIM}target{OFF}  {_target()}")
    for table, n in _counts(conn).items():
        print(f"  {table:<16} {n:>5}")
    conn.close()
    return verify()


def reset() -> int:
    """Drop everything and rebuild. The Postgres equivalent of `rm data/ctms.db`."""
    print(f"{DIM}target{OFF}  {_target()}")
    conn = db.connect()
    db.reset(conn)
    conn.close()
    print("dropped every table")
    return init()


def verify() -> int:
    conn = db.connect()
    try:
        result = audit.verify(conn)
    finally:
        conn.close()

    if not result["ok"]:
        print(f"{RED}chain broken at sequence {result['seq']}{OFF} — {result['error']}")
        return 1

    head = result["head"]
    print(f"{GREEN}chain intact{OFF} — {result['count']} events, head {head[:16]}…")
    if result["count"] == 8:
        same = head == EXPECTED_SEED_HEAD
        print(f"  {'matches' if same else RED + 'DIFFERS FROM' + OFF} the SQLite seed hash")
        return 0 if same else 1
    print(f"  {DIM}not the pristine seed ({result['count']} events), hash not compared{OFF}")
    return 0


COMMANDS = {"check": check, "init": init, "reset": reset, "verify": verify}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return 2
    try:
        return COMMANDS[sys.argv[1]]()
    except Exception as exc:  # noqa: BLE001
        # A connection failure is the common case here and the traceback is noise;
        # what the reader needs is which host failed and why.
        print(f"{RED}{type(exc).__name__}{OFF}: {str(exc).strip().splitlines()[0]}")
        if db.is_postgres():
            print(
                f"{DIM}If this is a timeout, check the URL is a Supabase *pooler* host "
                f"(...pooler.supabase.com). The direct db.<ref>.supabase.co host is "
                f"IPv6-only and unreachable from most networks and hosting tiers.{OFF}"
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
