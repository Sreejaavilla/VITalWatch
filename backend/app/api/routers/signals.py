"""/api/signals — DSMB safety signal view. OWNER: Sreeja."""


def aggregate_signals(user, study_id=None):
    """GET /api/signals -> AE counts aggregated by coded term x study x severity.

    Phase 4: replace raw counts with observed-vs-expected disproportionality.
    """
    raise NotImplementedError
