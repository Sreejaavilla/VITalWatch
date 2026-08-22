"""/api/kpi. OWNER: Kavin."""


def portfolio_kpis(user):
    """GET /api/kpi/portfolio -> KPISnapshot (the 6 headline numbers)."""
    raise NotImplementedError


def study_kpis(study_id, user):
    """GET /api/kpi/study/{id} -> KPISnapshot for one study."""
    raise NotImplementedError
