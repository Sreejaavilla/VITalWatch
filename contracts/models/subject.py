"""Subject — pseudonymous only. OWNER: Kavin.

DPDP Act 2023: no name, no date of birth, no identifier that resolves to a person.
`subject_code` is the only handle. This model has no name field and must never get one —
the schema-level absence is the compliance answer, and `extra="forbid"` on CTMSModel
means an attempt to attach one fails validation rather than passing quietly.
"""

from datetime import date
from enum import Enum

from .common import CTMSModel


class SubjectStatus(str, Enum):
    SCREENED = "screened"
    SCREEN_FAILED = "screen_failed"
    ENROLLED = "enrolled"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class Subject(CTMSModel):
    id: str
    #: e.g. "AIIA-003-014" — site-scoped, non-identifying, safe to show any role.
    subject_code: str
    study_id: str
    site_id: str

    screened_date: date
    #: None if screen-failed or still in screening.
    enrolled_date: date | None = None
    status: SubjectStatus
    #: Randomisation arm. None until enrolled.
    arm: str | None = None

    #: Age band, not date of birth — enough for SDTM DM, not enough to identify anyone.
    age_band: str | None = None
    sex: str | None = None

    consent_version: str
    consent_date: date
