"""Protocol deviation. OWNER: Kavin.

Major and critical deviations are reportable to the Ethics Committee; `reported_to_ec`
being false on a critical deviation is exactly the kind of thing this dashboard exists
to surface.
"""

from datetime import date
from enum import Enum

from .common import CTMSModel


class DeviationSeverity(str, Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class Deviation(CTMSModel):
    id: str
    study_id: str
    site_id: str
    subject_code: str | None = None

    category: str
    description: str
    detected_date: date
    severity: DeviationSeverity

    reported_to_ec: bool = False
    reported_date: date | None = None
    resolution: str | None = None
