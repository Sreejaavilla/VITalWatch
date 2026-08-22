"""Milestone — lifecycle checkpoints per study. OWNER: Kavin."""

from datetime import date
from enum import Enum

from .common import CTMSModel


class MilestoneType(str, Enum):
    EC_APPROVAL = "ec_approval"
    CTRI_REGISTRATION = "ctri_registration"
    FIRST_SITE_ACTIVATED = "first_site_activated"
    FIRST_SUBJECT_IN = "first_subject_in"
    FIFTY_PCT_ENROLLED = "fifty_pct_enrolled"
    LAST_SUBJECT_IN = "last_subject_in"
    DATABASE_LOCK = "database_lock"
    CLOSE_OUT = "close_out"


class MilestoneStatus(str, Enum):
    PLANNED = "planned"
    ACHIEVED = "achieved"
    AT_RISK = "at_risk"
    MISSED = "missed"


class Milestone(CTMSModel):
    id: str
    study_id: str
    type: MilestoneType
    planned_date: date
    actual_date: date | None = None
    status: MilestoneStatus
    #: Which role is accountable — drives "what do I owe" on a role dashboard.
    owner_role: str | None = None
