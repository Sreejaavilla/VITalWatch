"""Site — a participating centre. OWNER: Kavin."""

from datetime import date
from enum import Enum

from .common import CTMSModel


class SiteStatus(str, Enum):
    PLANNED = "planned"
    ACTIVATED = "activated"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class Site(CTMSModel):
    id: str
    name: str
    city: str
    state: str
    status: SiteStatus
    #: None until the site is activated. Drives the "sites activated" portfolio KPI.
    activated_date: date | None = None
    pi_name: str
    #: Planned enrolment capacity, used to spread a study's target across sites.
    capacity: int
    study_ids: list[str] = []
