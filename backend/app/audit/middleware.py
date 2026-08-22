"""Auto-audit every mutating request. OWNER: Caleb.

Every POST/PATCH/DELETE that succeeds writes an audit event with before and after
values. A mutating endpoint with no audit event is a bug, not an oversight.
"""


def audit_mutations(request, call_next):
    """ASGI middleware: capture before-state, run handler, append the audit event."""
    raise NotImplementedError
