"""AdverseEvent / SAE. OWNER: Kavin (shape) / Sreeja (behaviour).

Two things make this model different from a plain event record:

1. **Coding provenance is explicit.** `coding_source` records whether a term came from
   our curated mock dictionary or a licensed one. We do not have MedDRA/WHODrug, and
   the data says so rather than implying otherwise.
2. **Statutory clocks are fields, not UI.** NDCT Rules 2019 requires an SAE to reach the
   Ethics Committee and licensing authority within 24 hours, with a narrative in 14 days.
   Those deadlines are computed server-side on intake and stored here.
"""

from datetime import date, datetime
from enum import Enum

from .common import CTMSModel


class AESeverity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class AECausality(str, Enum):
    """WHO-UMC causality categories."""

    UNRELATED = "unrelated"
    UNLIKELY = "unlikely"
    POSSIBLE = "possible"
    PROBABLE = "probable"
    CERTAIN = "certain"


class AEOutcome(str, Enum):
    RECOVERED = "recovered"
    RECOVERING = "recovering"
    NOT_RECOVERED = "not_recovered"
    RECOVERED_WITH_SEQUELAE = "recovered_with_sequelae"
    FATAL = "fatal"
    UNKNOWN = "unknown"


class CodingSource(str, Enum):
    """Where a coded term came from. Shown in the UI — we never imply a licensed dictionary."""

    MOCK = "mock"          # curated subset, exact/fuzzy match
    SEMANTIC = "semantic"  # curated subset, embedding nearest-neighbour
    MEDDRA = "meddra"      # licensed. Not available in this build.
    UNCODED = "uncoded"


class TimelineStatus(str, Enum):
    ON_TRACK = "on_track"
    DUE_SOON = "due_soon"
    BREACHED = "breached"
    NOT_APPLICABLE = "not_applicable"  # non-serious AEs carry no statutory clock


class AdverseEvent(CTMSModel):
    id: str
    study_id: str
    site_id: str
    subject_code: str

    #: Free text as reported. This is what the coding service consumes.
    narrative: str
    onset_date: date
    serious: bool = False
    severity: AESeverity
    causality: AECausality
    outcome: AEOutcome

    # --- coding (Sreeja) ---
    coded_term: str | None = None
    coded_code: str | None = None
    coding_confidence: float | None = None
    coding_source: CodingSource = CodingSource.UNCODED

    suspect_drug: str | None = None
    drug_code: str | None = None
    drug_coding_source: CodingSource = CodingSource.UNCODED

    # --- statutory clocks (Sreeja), server-computed on intake ---
    reported_at: datetime
    #: Both None when serious is False.
    deadline_24h: datetime | None = None
    deadline_14d: datetime | None = None
    timeline_status: TimelineStatus = TimelineStatus.NOT_APPLICABLE
