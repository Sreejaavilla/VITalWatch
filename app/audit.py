"""Hash-chained, append-only audit trail.

Each row stores the hash of the row before it, so the log is a chain:

    hash_n = sha256(canonical_json(payload_n) + prev_hash_n)

Change any historical row — a value, a timestamp, an actor — and its hash no longer
matches what the next row committed to. The chain breaks at exactly the tampered row,
and `verify` reports its sequence number. Deleting a row instead leaves a gap in `seq`,
which is itself the finding.

Canonical JSON (sorted keys, no incidental whitespace) matters: two dicts that mean the
same thing must hash the same, or verification fails on formatting rather than tampering.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from typing import Any

from .models import GENESIS_HASH, AuditAction, AuditEvent, utcnow


def canonical_json(payload: dict[str, Any]) -> str:
    """Deterministic serialisation. Sorted keys, tight separators, no ASCII escaping."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False)


def compute_hash(payload: dict[str, Any], prev_hash: str) -> str:
    return hashlib.sha256((canonical_json(payload) + prev_hash).encode("utf-8")).hexdigest()


def _payload(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    """The hashed fields. `hash` and `prev_hash` are excluded — one is the output, the
    other is mixed in separately."""
    return {
        "seq": row["seq"],
        "actor": row["actor"],
        "action": row["action"],
        "resource_type": row["resource_type"],
        "resource_id": row["resource_id"],
        "before_json": row["before_json"],
        "after_json": row["after_json"],
        "timestamp_utc": row["timestamp_utc"],
        "reason": row["reason"],
    }


def head(conn: sqlite3.Connection) -> tuple[int, str]:
    """Sequence number and hash of the last row. `(0, GENESIS_HASH)` on an empty chain."""
    row = conn.execute("SELECT seq, hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
    return (row["seq"], row["hash"]) if row else (0, GENESIS_HASH)


def record(
    conn: sqlite3.Connection,
    *,
    actor: str,
    action: AuditAction | str,
    resource_type: str,
    resource_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    timestamp: str | None = None,
    commit: bool = True,
) -> AuditEvent:
    """Append one event. The only way rows enter this table.

    `timestamp` exists so the seeder can lay down a plausible history; application code
    never passes it, and the server clock is used instead — ALCOA+ 'contemporaneous'.
    """
    prev_seq, prev_hash = head(conn)
    row = {
        "seq": prev_seq + 1,
        "actor": actor,
        "action": action.value if isinstance(action, AuditAction) else action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "before_json": canonical_json(before) if before is not None else None,
        "after_json": canonical_json(after) if after is not None else None,
        "timestamp_utc": timestamp or utcnow().isoformat(),
        "reason": reason,
    }
    row_hash = compute_hash(_payload(row), prev_hash)
    conn.execute(
        """INSERT INTO audit_events
           (id, seq, actor, action, resource_type, resource_id,
            before_json, after_json, timestamp_utc, reason, prev_hash, hash)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()), row["seq"], row["actor"], row["action"],
            row["resource_type"], row["resource_id"], row["before_json"],
            row["after_json"], row["timestamp_utc"], row["reason"], prev_hash, row_hash,
        ),
    )
    if commit:
        conn.commit()
    return AuditEvent(
        id=str(uuid.uuid4()), seq=row["seq"], actor=actor,
        action=AuditAction(row["action"]), resource_type=resource_type,
        resource_id=resource_id, before=before, after=after,
        timestamp_utc=row["timestamp_utc"], reason=reason,
        prev_hash=prev_hash, hash=row_hash,
    )


def verify(conn: sqlite3.Connection) -> dict[str, Any]:
    """Walk the chain from genesis.

    Returns `{"ok": True, "count": n}`, or `ok: False` with the sequence number of the
    first row that fails and why. Three distinct failures are reported separately
    because they mean different things: a broken link means a row was edited, a gap
    means a row was deleted, a bad hash means the row's own contents were changed.
    """
    prev_hash = GENESIS_HASH
    expected_seq = 1
    count = 0

    for row in conn.execute("SELECT * FROM audit_events ORDER BY seq ASC"):
        if row["seq"] != expected_seq:
            return {
                "ok": False, "seq": row["seq"], "count": count,
                "error": f"sequence gap: expected {expected_seq}, found {row['seq']} — "
                         f"{row['seq'] - expected_seq} row(s) deleted",
            }
        if row["prev_hash"] != prev_hash:
            return {
                "ok": False, "seq": row["seq"], "count": count,
                "error": "broken link: prev_hash does not match the preceding row's hash",
            }
        if compute_hash(_payload(row), prev_hash) != row["hash"]:
            return {
                "ok": False, "seq": row["seq"], "count": count,
                "error": "content altered: this row's contents no longer hash to its stored hash",
            }
        prev_hash = row["hash"]
        expected_seq += 1
        count += 1

    return {"ok": True, "count": count, "head": prev_hash}


if __name__ == "__main__":
    import sys

    from .db import connect

    # `--verify` is accepted because that is how the command is written down in
    # ROADMAP.md and the demo script. Verifying is the only thing this module does from
    # the command line, so the flag is optional rather than required.
    if set(sys.argv[1:]) - {"--verify"}:
        print("usage: python -m app.audit [--verify]")
        raise SystemExit(2)

    conn = connect()
    result = verify(conn)
    if result["ok"]:
        print(f"OK — {result['count']} events, chain intact")
        print(f"head {result['head']}")
    else:
        print(f"TAMPERED at seq {result['seq']} — {result['error']}")
        print(f"{result['count']} event(s) verified before the break")
        raise SystemExit(1)
