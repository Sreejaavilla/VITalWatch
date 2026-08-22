"""KPI computation. OWNER: Kavin.

Phase 1 reads fixtures. Phase 2 reads Postgres. The function signatures do not change
between the two — that is the point.
"""


def portfolio_snapshot():
    """active_studies, enrolled_total, target_total, sites_activated,
    open_queries, overdue_monitoring_visits, open_saes."""
    raise NotImplementedError


def study_snapshot(study_id):
    """enrolment_pct, screen_failure_rate, visit_compliance_pct,
    open_query_ageing_days, deviation_rate_per_site, days_to_next_milestone."""
    raise NotImplementedError
