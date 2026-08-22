"""KPI models. OWNER: Kavin.

Two concrete shapes rather than one loose bag of numbers, so Ishan gets typed fields
and a missing metric fails at the API instead of rendering as `undefined` on stage.

`KPISnapshot` is the union both endpoints are documented against; endpoints return the
concrete type — `/api/kpi/portfolio` -> PortfolioKPI, `/api/kpi/study/{id}` -> StudyKPI.
"""

from datetime import datetime

from .common import CTMSModel


class PortfolioKPI(CTMSModel):
    """The six headline numbers on the portfolio screen."""

    generated_at: datetime
    active_studies: int
    enrolled_total: int
    target_total: int
    sites_activated: int
    sites_total: int
    open_queries: int
    overdue_monitoring_visits: int
    open_saes: int

    @property
    def enrolment_pct(self) -> float:
        return 0.0 if self.target_total == 0 else 100.0 * self.enrolled_total / self.target_total


class StudyKPI(CTMSModel):
    """Per-study drill-down metrics."""

    generated_at: datetime
    study_id: str
    enrolment_pct: float
    enrolled: int
    target: int
    #: Enrolment the plan says we should have hit by today. The gap drives the lag alert.
    expected_by_today: int
    screen_failure_rate: float
    visit_compliance_pct: float
    open_queries: int
    open_query_ageing_days: float
    deviation_rate_per_site: float
    open_saes: int
    days_to_next_milestone: int | None = None
    next_milestone: str | None = None


#: Documented response type for the KPI endpoints.
KPISnapshot = PortfolioKPI | StudyKPI
