"""Immutable, hash-chained audit trail. OWNER: Caleb.

The technical heart of the pitch. Judges will ask "what stops someone editing the
database directly?" — the answer is this file plus scripts/verify_audit.sh.

    row.hash = sha256(canonical_json(payload) + prev_hash)

Append-only: no UPDATE, no DELETE. Enforce it with a DB trigger too (db/schema.sql),
so the guarantee doesn't depend on the application behaving.

ALCOA+: attributable (actor_id + role), legible, contemporaneous (server UTC clock,
never client-supplied), original (before/after captured at write), accurate.
"""

GENESIS_HASH = "0" * 64


def compute_hash(payload, prev_hash):
    """sha256 over canonical JSON of payload concatenated with prev_hash."""
    raise NotImplementedError


def append(actor_id, actor_role, action, resource_type, resource_id,
           before=None, after=None, reason=None):
    """Write one audit event, chained to the current tail. Returns the event."""
    raise NotImplementedError


def verify():
    """Walk the whole chain. Return (True, None) or (False, seq_of_first_bad_row)."""
    raise NotImplementedError
