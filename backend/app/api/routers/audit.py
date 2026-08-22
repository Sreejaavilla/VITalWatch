"""/api/audit. OWNER: Caleb.

This endpoint is the pitch. Judges will click it and then try to break it.

PHASE 0 PLACEHOLDER — returns seeded events and a hardcoded verify result. Caleb
replaces both with the real hash chain (backend/app/audit/chain.py).
"""

from fastapi import APIRouter
from pydantic import BaseModel

from contracts.models import AuditEvent
from ...stubs import loader

router = APIRouter(prefix="/api/audit", tags=["audit"])


class ChainVerification(BaseModel):
    """`broken_at` is the sequence number of the first tampered row, or None."""

    ok: bool
    checked: int
    broken_at: int | None = None


@router.get("", response_model=list[AuditEvent], summary="Audit trail, newest first")
def list_audit_events(
    actor: str | None = None,
    role: str | None = None,
) -> list[AuditEvent]:
    records = loader.load("audit_events")
    if actor:
        records = [e for e in records if e["actor_id"] == actor]
    if role:
        records = [e for e in records if e["actor_role"] == role]
    return [AuditEvent(**e) for e in sorted(records, key=lambda e: e["seq"], reverse=True)]


@router.get("/verify", response_model=ChainVerification, summary="Verify the hash chain")
def verify_chain() -> ChainVerification:
    """PLACEHOLDER: always ok. Caleb: recompute hash(payload + prev_hash) down the chain.

    Pressing this live after tampering with a row is the strongest 15 seconds of the demo.
    """
    return ChainVerification(ok=True, checked=len(loader.load("audit_events")), broken_at=None)
