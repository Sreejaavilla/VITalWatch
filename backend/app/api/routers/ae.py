"""/api/ae — adverse event intake. OWNER: Sreeja.

Thin wrapper. All behaviour lives in services/pv/ so Sreeja can run and test it
with the backend completely down.
"""


def report_ae(payload, user):
    """POST /api/ae -> AdverseEvent.

    Codes the narrative via services.pv.coding, computes NDCT-2019 reporting
    deadlines via services.pv.timelines, and writes an audit event.
    """
    raise NotImplementedError


def list_aes(user, study_id=None, serious=None):
    """GET /api/ae -> AdverseEvent[]."""
    raise NotImplementedError


def get_ae(ae_id, user):
    """GET /api/ae/{id} -> AdverseEvent."""
    raise NotImplementedError


def suggest_coding(narrative, user):
    """POST /api/coding/suggest -> {candidates: [{term, code, score}]} (top 3)."""
    raise NotImplementedError
