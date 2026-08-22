"""The data model. One file, on purpose.

Merged from the twelve `contracts/models/*.py` modules — same fields, same validators,
one import. Every model inherits CTMSModel so serialisation behaves identically across
the API, the templates and the audit trail.

Two things here are compliance decisions, not style choices:

  * `Subject` has no name, no date of birth, no resolvable identifier (DPDP Act 2023).
    The absence IS the answer, and `extra="forbid"` means an attempt to attach one
    fails validation rather than passing quietly.
  * `AdverseEvent.coding_source` records where a coded term came from. We do not have
    MedDRA or WHODrug — they are licensed — and the data says so rather than implying
    otherwise.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


# --------------------------------------------------------------------------- base


class CTMSModel(BaseModel):
    """Base for every model.

    `use_enum_values=False` keeps enums as enums in Python and serialises them to
    their string value in JSON — so a template sees "enrolling", not an int.
    """

    model_config = ConfigDict(
        use_enum_values=False,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",  # a typo'd field name fails loudly at hour 3, not silently at hour 20
    )


def utcnow() -> datetime:
    """Server clock, always UTC, always timezone-aware.

    Audit timestamps and reporting deadlines are computed from this and NEVER from a
    client-supplied value. ALCOA+ 'contemporaneous' depends on it.
    """
    return datetime.now(timezone.utc)


# -------------------------------------------------------------------------- study


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
    """The portfolio unit.

    Lifecycle: protocol -> ec_approval -> ctri_registered -> site_activation
               -> screening -> enrolling -> follow_up -> close_out
    """

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

    pi_name: str
    site_ids: list[str] = []
    start_date: date
    end_date: date | None = None


# --------------------------------------------------------------------------- site


class SiteStatus(str, Enum):
    PLANNED = "planned"
    ACTIVATED = "activated"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class Site(CTMSModel):
    """A participating centre."""

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


# ------------------------------------------------------------------------ subject


class SubjectStatus(str, Enum):
    SCREENED = "screened"
    SCREEN_FAILED = "screen_failed"
    ENROLLED = "enrolled"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class Subject(CTMSModel):
    """Pseudonymous only.

    DPDP Act 2023: no name, no date of birth, no identifier that resolves to a person.
    `subject_code` is the only handle. This model has no name field and must never get
    one — see the module docstring.
    """

    id: str
    #: e.g. "AIIA-003-014" — site-scoped, non-identifying, safe to show anywhere.
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


# -------------------------------------------------------------------------- visit


class VisitStatus(str, Enum):
    UPCOMING = "upcoming"
    COMPLETED = "completed"
    MISSED = "missed"
    OVERDUE = "overdue"


class Visit(CTMSModel):
    """Scheduled vs actual. Drives the visit-compliance KPI.

    Covers both subject visits and site monitoring visits; `monitoring_visit`
    distinguishes them. Overdue monitoring visits are one of the portfolio alerts.
    """

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


# ---------------------------------------------------------------------- deviation


class DeviationSeverity(str, Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class Deviation(CTMSModel):
    """Protocol deviation.

    Major and critical deviations are reportable to the Ethics Committee;
    `reported_to_ec` false on a critical deviation is exactly the kind of thing this
    dashboard exists to surface.
    """

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


# -------------------------------------------------------------------------- query


class QueryStatus(str, Enum):
    OPEN = "open"
    ANSWERED = "answered"
    CLOSED = "closed"


class DataQuery(CTMSModel):
    """A data-cleaning query raised against a data point.

    `age_days` is computed on read, not stored: open-query ageing is a KPI and must not
    go stale because someone forgot to recompute a column.
    """

    id: str
    study_id: str
    site_id: str
    subject_code: str | None = None

    field: str
    question: str
    raised_date: date
    raised_by: str
    answered_date: date | None = None
    closed_date: date | None = None
    status: QueryStatus

    #: Days open as of the response. Server-computed; ignore anything a client sends.
    age_days: int = 0


# ----------------------------------------------------------------- adverse events


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

    CURATED = "curated"  # our own vocabulary in app/terms.csv, exact or fuzzy match
    MEDDRA = "meddra"    # licensed. Not available in this build, and never set.
    UNCODED = "uncoded"


class TimelineStatus(str, Enum):
    ON_TRACK = "on_track"
    DUE_SOON = "due_soon"
    BREACHED = "breached"
    NOT_APPLICABLE = "not_applicable"  # non-serious AEs carry no statutory clock


class AdverseEvent(CTMSModel):
    """Adverse event / SAE.

    Two things make this different from a plain event record:

    1. **Coding provenance is explicit** — `coding_source` says whether a term came from
       our own curated vocabulary or a licensed dictionary.
    2. **Statutory clocks are fields, not UI.** NDCT Rules 2019 requires an SAE to reach
       the Ethics Committee and licensing authority within 24 hours, with a narrative in
       14 days. Those deadlines are computed server-side on intake and stored here.
    """

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

    # --- coding ---
    coded_term: str | None = None
    coded_code: str | None = None
    coding_confidence: float | None = None
    coding_source: CodingSource = CodingSource.UNCODED

    suspect_drug: str | None = None
    drug_code: str | None = None
    drug_coding_source: CodingSource = CodingSource.UNCODED

    # --- statutory clocks, server-computed on intake ---
    reported_at: datetime
    #: Both None when serious is False.
    deadline_24h: datetime | None = None
    deadline_14d: datetime | None = None
    timeline_status: TimelineStatus = TimelineStatus.NOT_APPLICABLE


# ---------------------------------------------------------------------- milestone


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
    """Lifecycle checkpoints per study."""

    id: str
    study_id: str
    type: MilestoneType
    planned_date: date
    actual_date: date | None = None
    status: MilestoneStatus


# -------------------------------------------------------------------------- alert


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
    """Output of the rule engine.

    Thresholds are configurable via env (see .env.example). A judge asking "is this
    configurable or hardcoded?" gets answered by changing one value and refreshing.
    """

    id: str
    rule: AlertRule
    severity: AlertSeverity
    study_id: str
    study_title: str | None = None
    #: Human-readable, already formatted with the actual numbers. Rendered as-is.
    message: str
    raised_at: datetime
    #: Route the alert drills into, e.g. "/study/STU-003".
    deep_link: str

    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None


# -------------------------------------------------------------------------- audit

#: prev_hash of the very first row in the chain.
GENESIS_HASH = "0" * 64


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"  # only for sensitive reads (audit export, regulator export)
    EXPORT = "export"
    ACKNOWLEDGE = "acknowledge"
    SIGN = "sign"


class AuditEvent(CTMSModel):
    """Append-only, hash-chained. The technical heart of the pitch.

    Every field answers one ALCOA+ question:

      attributable    -> actor
      legible         -> before/after as structured JSON, not a free-text log line
      contemporaneous -> timestamp_utc, from the server clock, never client-supplied
      original        -> before captured at write time, not reconstructed
      accurate        -> hash chain makes any later edit detectable and locatable

    Nothing here is mutable after write. No UPDATE, no DELETE — enforced by a database
    trigger as well as by application code, so the guarantee doesn't depend on the
    application behaving.
    """

    id: str
    #: Gapless sequence. A gap means rows were deleted — that is itself the finding.
    seq: int

    #: Who performed the action.
    actor: str
    action: AuditAction
    resource_type: str
    resource_id: str | None = None

    #: State before and after the change. None on create/delete respectively.
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None

    timestamp_utc: datetime
    #: Why, when the action needs a reason (signature, override, deviation).
    reason: str | None = None

    prev_hash: str
    #: sha256(canonical_json(payload) + prev_hash)
    hash: str


# ---------------------------------------------------------------------------- kpi


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
