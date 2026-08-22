"""Single source of truth for the data model. OWNER: Kavin. FROZEN AT HOUR 2.

Breaking changes after the Phase 0 gate must be announced to the whole room —
backend, datagen, the PV module and the fixtures all import from here.

Verify:  python -c "from contracts.models import Study, Site, Subject, Visit, \
Deviation, DataQuery, AdverseEvent, Milestone, AuditEvent, User, Role, \
KPISnapshot, Alert"
"""

from .common import CTMSModel, utcnow
from .study import Study, StudyPhase, StudyStatus
from .site import Site, SiteStatus
from .subject import Subject, SubjectStatus
from .visit import Visit, VisitStatus
from .deviation import Deviation, DeviationSeverity
from .query import DataQuery, QueryStatus
from .ae import (
    AdverseEvent,
    AECausality,
    AEOutcome,
    AESeverity,
    CodingSource,
    TimelineStatus,
)
from .milestone import Milestone, MilestoneStatus, MilestoneType
from .audit import GENESIS_HASH, AuditAction, AuditEvent
from .user import READ_ONLY_ROLES, Role, User
from .kpi import KPISnapshot, PortfolioKPI, StudyKPI
from .alert import Alert, AlertRule, AlertSeverity

__all__ = [
    "CTMSModel", "utcnow",
    "Study", "StudyPhase", "StudyStatus",
    "Site", "SiteStatus",
    "Subject", "SubjectStatus",
    "Visit", "VisitStatus",
    "Deviation", "DeviationSeverity",
    "DataQuery", "QueryStatus",
    "AdverseEvent", "AESeverity", "AECausality", "AEOutcome",
    "CodingSource", "TimelineStatus",
    "Milestone", "MilestoneType", "MilestoneStatus",
    "AuditEvent", "AuditAction", "GENESIS_HASH",
    "User", "Role", "READ_ONLY_ROLES",
    "KPISnapshot", "PortfolioKPI", "StudyKPI",
    "Alert", "AlertRule", "AlertSeverity",
]
