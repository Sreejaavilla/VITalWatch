"""Role-based access control. OWNER: Caleb.

Reads contracts/roles.yaml. NEVER hardcode a role inside a route handler — if a
permission question can't be answered by reading roles.yaml, the matrix is wrong.

Acceptance test (Phase 1): a study_coordinator token gets 403 on
GET /api/export/sdtm; a regulator token gets 200.
"""


def load_matrix():
    """Parse contracts/roles.yaml into {resource: {action: set(roles)}}. Default deny."""
    raise NotImplementedError


def require(resource, action):
    """Dependency factory -> raises 403 unless the caller's role permits action on resource."""
    raise NotImplementedError


def scope_filter(user, queryset_or_rows):
    """Narrow results to the caller's scope: own_studies / own_sites / assigned / all."""
    raise NotImplementedError


def deny_mutations(user):
    """Regulator role: 403 on every POST/PATCH/DELETE. No exceptions, no override."""
    raise NotImplementedError
