"""Visit — scheduled vs actual. Drives the visit-compliance KPI. OWNER: Kavin.

Covers both subject visits and site monitoring visits; `monitoring_visit` distinguishes
them. Overdue monitoring visits are one of the three configurable portfolio alerts.
"""

from datetime import date
from enum import Enum

from .common import CTMSModel


class VisitStatus(str, Enum):
    UPCOMING = "upcoming"
    COMPLETED = "completed"
    MISSED = "missed"
    OVERDUE = "overdue"


class Visit(CTMSModel):
    id: str
    study_id: str
    site_id: str
    #: None for a site monitoring visit — those aren't tied to a subject.
    subject_code: str | None = None

    visit_name: str
    scheduled_date: date
    actual_date: date | None = None
    #: Protocol-defined window. Outside it, the visit is a deviation.
    window_days: int = 0
    status: VisitStatus

    monitoring_visit: bool = False
    #: A monitoring visit with actual_date set but no report filed is still overdue.
    report_filed: bool = False
