"""/api/audit. OWNER: Caleb.

This endpoint is the pitch. Judges will click it and then try to break it.
"""


def list_audit_events(user, actor=None, role=None, date_from=None, date_to=None):
    """GET /api/audit -> AuditEvent[], newest first, with before/after values."""
    raise NotImplementedError


def verify_chain(user):
    """GET /api/audit/verify -> {ok: bool, broken_at: int | None}.

    Recomputes hash(payload + prev_hash) down the whole chain. Any row mutated
    out of band makes this return the exact sequence number where it broke.
    """
    raise NotImplementedError


def export_audit(user):
    """GET /api/audit/export -> CSV. Regulator and admin only. Phase 4."""
    raise NotImplementedError
