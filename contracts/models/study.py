"""Study — the portfolio unit. OWNER: Kavin.

Lifecycle: protocol -> ec_approval -> ctri_registered -> site_activation
           -> screening -> enrolling -> follow_up -> close_out
"""

from datetime import date
from enum import Enum

from .common import CTMSModel


class StudyPhase(str, Enum):
    PHASE_I = "I"
    PHASE_II = "II"
    PHASE_III = "III"
    PHASE_IV = "IV"
    #: Ayurveda portfolios carry observational and pilot studies that aren't phased.
    OBSERVATIONAL = "observational"


class StudyStatus(str, Enum):
    PROTOCOL = "protocol"
    EC_APPROVAL = "ec_approval"
    CTRI_REGISTERED = "ctri_registered"
    SITE_ACTIVATION = "site_activation"
    SCREENING = "screening"
    ENROLLING = "enrolling"
    FOLLOW_UP = "follow_up"
    CLOSE_OUT = "close_out"


class Study(CTMSModel):
    id: str
    title: str
    protocol_no: str
    #: None until prospectively registered. A study enrolling without one is a finding.
    ctri_number: str | None = None
    phase: StudyPhase
    status: StudyStatus
    therapeutic_area: str

    ec_approval_date: date | None = None
    #: The ethics-renewal alert fires off this field. Never leave it null on an active study.
    ec_expiry_date: date | None = None
    ctri_registration_date: date | None = None

    target_enrolment: int
    actual_enrolment: int = 0

    pi_id: str
    site_ids: list[str] = []
    start_date: date
    end_date: date | None = None
