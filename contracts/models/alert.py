"""Alert — output of the rule engine. OWNER: Kavin.

Thresholds are configurable via env (see .env.example). A judge asking "is this
configurable or hardcoded?" gets answered by changing one value and refreshing.
"""

from datetime import datetime
from enum import Enum

from .common import CTMSModel


class AlertRule(str, Enum):
    ENROLMENT_LAG = "enrolment_lag"
    ETHICS_RENEWAL_DUE = "ethics_renewal_due"
    CTRI_UPDATE_DUE = "ctri_update_due"
    MONITORING_VISIT_OVERDUE = "monitoring_visit_overdue"
    SAE_TIMELINE_BREACH = "sae_timeline_breach"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(CTMSModel):
    id: str
    rule: AlertRule
    severity: AlertSeverity
    study_id: str
    study_title: str | None = None
    #: Human-readable, already formatted with the actual numbers. Ishan renders it as-is.
    message: str
    raised_at: datetime
    #: Frontend route the alert drills into, e.g. "/study/STU-003".
    deep_link: str

    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
