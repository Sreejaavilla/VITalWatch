"""Configurable alert rules. OWNER: Kavin.

Thresholds come from env (see .env.example) — a judge asking "is this configurable?"
should be answered by changing one value and refreshing the dashboard.
"""


def rule_enrolment_lag(study, threshold_pct):
    """Fire when actual enrolment < threshold_pct of the expected-by-today curve."""
    raise NotImplementedError


def rule_ethics_renewal_due(study, days):
    """Fire when EC approval or CTRI registration needs updating within `days`."""
    raise NotImplementedError


def rule_monitoring_visit_overdue(visits, grace_days):
    """Fire when a scheduled monitoring visit is past due with no report filed."""
    raise NotImplementedError


def evaluate_all():
    """Run every rule across the portfolio, persist and return severity-ranked Alerts."""
    raise NotImplementedError
