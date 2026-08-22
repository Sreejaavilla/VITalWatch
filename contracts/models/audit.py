"""AuditEvent — append-only, hash-chained. OWNER: Kavin (shape) / Caleb (writer).

The technical heart of the pitch. Every field here exists to answer one ALCOA+ question:

  attributable   -> actor_id, actor_role
  legible        -> before/after as structured JSON, not a free-text log line
  contemporaneous-> timestamp_utc, from the server clock, never client-supplied
  original       -> before captured at write time, not reconstructed
  accurate       -> hash chain makes any later edit detectable and locatable

Nothing in this model is mutable after write. No UPDATE, no DELETE — enforced by a
database trigger as well as by application code, so the guarantee doesn't depend on
the application behaving.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from .common import CTMSModel

#: prev_hash of the very first row in the chain.
GENESIS_HASH = "0" * 64


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    VIEW = "view"          # only for sensitive reads (audit export, regulator export)
    EXPORT = "export"
    ACKNOWLEDGE = "acknowledge"
    SIGN = "sign"          # electronic signature, Phase 4
    ACCESS_DENIED = "access_denied"  # a 403 is a security event worth keeping


class AuditEvent(CTMSModel):
    id: str
    #: Gapless sequence. A gap means rows were deleted — that is itself the finding.
    seq: int

    actor_id: str
    actor_role: str
    action: AuditAction
    resource_type: str
    resource_id: str | None = None

    #: State before and after the change. None on create/delete respectively.
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None

    timestamp_utc: datetime
    #: Why, when the action needs a reason (signature, override, deviation).
    reason: str | None = None

    prev_hash: str
    #: sha256(canonical_json(payload) + prev_hash)
    hash: str
