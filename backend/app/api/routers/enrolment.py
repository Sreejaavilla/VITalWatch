"""/api/enrolment. OWNER: Kavin."""


def enrolment_curve(study_id, user):
    """GET /api/enrolment/{study_id} -> {actual[], expected[], target}.

    `expected` is the planned curve; the gap between it and `actual` is what the
    enrolment-lag alert fires on.
    """
    raise NotImplementedError
