"""The AYU-008 investigation case: one trial, shaped to be investigated.

Constants only, and no imports from anywhere else in the application. Both the generator
(`datagen`) and the investigation feature (`investigation`) need these facts, and
`kpi` already imports `datagen`, so anything with application imports in it here would
close an import cycle.

**Everything below is invented**, including the intervention, the constituents, the
historical trials and the literature. AYU-008 is not a real formulation and the
"constituents" are designations, not plants — naming a real herb next to a fabricated
liver signal would be a genuinely harmful thing to put on a screen, however clearly the
page were labelled. The safety concepts (transaminase monitoring, dechallenge, Hy's law)
are real clinical practice; their application to AYU-008 is fiction.
"""

from __future__ import annotations

CASE_ID = "INV-001"
STUDY_ID = "AYU-008"

INTERVENTION = "AYU-008"
FORMULATION = "Ayurvedic polyherbal formulation"
INDICATION = "Madhumeha (Type 2 Diabetes Mellitus)"
TITLE = f"{INDICATION} — {INTERVENTION}"
THERAPEUTIC_AREA = "Metabolic"
PHASE = "II"
PROTOCOL_NO = "AIIA/CTP/2026/09"
CTRI_NUMBER = "CTRI/2026/02/041887"
PI_NAME = "Dr. A. Nair"

TARGET_ENROLMENT = 500
ACTUAL_ENROLMENT = 137

#: Chosen so the straight-line plan in `kpi` lands on exactly 240 by TODAY, which makes
#: the recruitment deviation −42.9%. Verified by `scripts/rehearse.py` rather than
#: trusted: change `ENROLMENT_WINDOW_DAYS` and this date has to move with it.
START_DATE = "2026-02-11"
EXPECTED_BY_TODAY = 240

PROTOCOL = {
    "Intervention": "AYU-008, standardised polyherbal formulation",
    "Dosage": "500 mg twice daily, oral",
    "Duration": "24 weeks",
    "Population": "Adults aged 30–65 with confirmed T2DM",
    "Design": "Phase II randomised, parallel-group, active-controlled",
    "Monitoring": "Liver function tests at baseline and every 8 weeks",
}

#: The protocol clause the investigation surfaces. Phrased as an observation about
#: timing, not a judgement about adequacy — the system has no basis for the latter and
#: saying so would be the system making a clinical determination it is not entitled to.
PROTOCOL_OBSERVATION = (
    "Liver function is scheduled at baseline and every 8 weeks. All three events were "
    "detected between day 41 and day 49 — inside the first monitoring interval, before "
    "the week-8 test. Flagged for investigator review of monitoring frequency in light "
    "of the observed pattern; no determination of adequacy is made here."
)

#: Contributing factors the recruitment evidence lists. Each is a hypothesis for a human
#: to check, not a finding — the data shows the shortfall, not its cause.
RECRUITMENT_FACTORS = [
    ("Eligibility criteria", "Narrow age window (30–65) with confirmed diagnosis required at screening."),
    ("Site variation", "Enrolment is concentrated in a minority of activated sites."),
    ("Screening failures", "Screen-failure rate above the portfolio median."),
    ("Enrolment velocity", "Subjects per site per month below the rate the plan assumes."),
]

#: (subject number within the study, narrative as a site would write it, day on study,
#: severity). The narratives are deliberately written three different ways: they are
#: coded live by `pv.code`, and all three landing on the same term is the point being
#: demonstrated. Verified in `scripts/rehearse.py`.
AE_CASES = [
    (31, "raised ALT on scheduled bloods, asymptomatic", 41, "moderate"),
    (84, "deranged LFT with raised ALT at follow-up", 46, "moderate"),
    (119, "raised ALT and AST on routine monitoring bloods", 49, "moderate"),
]

#: What the four indicators on the case file mean. The values are computed from the
#: database at request time; only the wording lives here.
INDICATORS = [
    ("Recruitment", "recruitment", "Enrolment against the plan-to-date figure."),
    ("Adverse events", "events", "Similar coded events within a comparable window."),
    ("Safety signal", "signal", "Disproportionality screen on coded terms."),
    ("Protocol", "protocol", "Monitoring schedule against the observed event timing."),
]

DECISIONS = {
    "acknowledge": ("Acknowledge", "No further action at this time; pattern noted."),
    "review": ("Review further", "Assign for detailed review before determining action."),
    "escalate": ("Escalate", "Refer for formal safety assessment."),
}

ESCALATION_REASONS = [
    "Potential emerging safety pattern requiring further assessment.",
    "Monitoring schedule to be reviewed against observed event timing.",
    "Refer to Data Safety Monitoring Board at next scheduled review.",
    "Request unblinded review of hepatic parameters.",
]
