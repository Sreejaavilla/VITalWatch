"""Studies, sites and milestones. OWNER: Roxy."""

from datetime import date, timedelta
import random

# Fixed demo anchor: every date in the portfolio is derived from this, never from
# date.today(), so the seed alone reproduces the whole dataset on any machine.
DEMO_ANCHOR = date(2026, 8, 24)

STUDY_TITLES = [
    ("Ashwagandha for generalised anxiety disorder", "II", "psychiatry"),
    ("Triphala in type-2 diabetes adjunct therapy", "III", "endocrinology"),
    ("Turmerone-rich Curcuma oil in knee osteoarthritis", "II", "rheumatology"),
    ("Brahmi cognitive support in mild cognitive impairment", "II", "neurology"),
    ("Guduchi immunomodulation post-viral recovery", "I", "immunology"),
    ("Punarnava-based formulation in early CKD", "observational", "nephrology"),
    ("Sitopaladi churna in chronic allergic rhinitis", "III", "respiratory"),
    ("Arjuna Ksheera paka in stable angina", "II", "cardiology"),
]

STATES = [
    ("New Delhi", "Delhi"), ("Mumbai", "Maharashtra"), ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"), ("Chennai", "Tamil Nadu"), ("Kolkata", "West Bengal"),
    ("Bengaluru", "Karnataka"), ("Hyderabad", "Telangana"), ("Pune", "Maharashtra"),
    ("Ahmedabad", "Gujarat"), ("Guwahati", "Assam"), ("Thiruvananthapuram", "Kerala"),
]

PI_NAMES = [
    "Dr. A. Sharma", "Dr. V. Iyer", "Dr. S. Nair", "Dr. R. Deshpande",
    "Dr. M. Reddy", "Dr. P. Bose", "Dr. K. Menon", "Dr. L. Gupta",
    "Dr. T. Joshi", "Dr. D. Chauhan", "Dr. N. Pillai", "Dr. B. Rao",
]

LIFECYCLE = ["protocol", "ec_approval", "ctri_registered", "site_activation",
             "screening", "enrolling", "follow_up", "close_out"]

MILESTONE_ORDER = ["ec_approval", "ctri_registration", "first_site_activated",
                   "first_subject_in", "fifty_pct_enrolled", "last_subject_in",
                   "database_lock", "close_out"]

MILESTONE_OWNERS = {
    "ec_approval": "ethics_committee",
    "ctri_registration": "principal_investigator",
    "first_site_activated": "study_coordinator",
    "first_subject_in": "principal_investigator",
    "fifty_pct_enrolled": "study_coordinator",
    "last_subject_in": "principal_investigator",
    "database_lock": "admin",
    "close_out": "monitor",
}


def make_studies(n, rng):
    """Ayurveda trials across phases with EC/CTRI dates and enrolment targets.

    The portfolio tells a story (see datagen/README.md):
      * STU-001 and STU-002 lag enrolment (enrolment.py sets their lag_factor)
      * STU-003 has EC approval expiring inside 30 days of DEMO_ANCHOR
    """
    titles = STUDY_TITLES[:]
    rng.shuffle(titles)
    studies = []
    for i in range(n):
        title, phase, area = titles[i % len(titles)]
        sid = f"STU-{i + 1:03d}"
        stage_idx = rng.randint(3, len(LIFECYCLE) - 2)  # nothing pre-site_activation, none closed
        status = LIFECYCLE[stage_idx]
        start = DEMO_ANCHOR - timedelta(days=rng.randint(200, 540))
        ec_approval = start - timedelta(days=rng.randint(60, 120))
        ctri_reg = ec_approval - timedelta(days=1)
        target = rng.choice([50, 60, 80, 90, 100, 120])
        if i == 2:  # the ethics-renewal alert story: expiring within 30 days
            ec_expiry = DEMO_ANCHOR + timedelta(days=rng.randint(10, 28))
            stage_idx = LIFECYCLE.index("enrolling")
            status = LIFECYCLE[stage_idx]
        else:
            ec_expiry = ec_approval + timedelta(days=rng.randint(365, 730))
        study = {
            "id": sid,
            "title": title,
            "protocol_no": f"AIIA/{start.year}/{rng.randint(10, 99):02d}",
            "ctri_number": f"CTRI/{start.year}/{rng.randint(1, 12):02d}/{rng.randint(1000, 9999)}",
            "phase": phase,
            "status": status,
            "therapeutic_area": area,
            "ec_approval_date": ec_approval.isoformat(),
            "ec_expiry_date": ec_expiry.isoformat(),
            "ctri_registration_date": ctri_reg.isoformat(),
            "target_enrolment": target,
            "actual_enrolment": 0,
            "pi_id": "",
            "site_ids": [],
            "start_date": start.isoformat(),
            "end_date": None,
        }
        # pi_id and site_ids are wired after sites exist (run.py)
        studies.append(study)
    return studies


def make_sites(n, rng):
    sites = []
    for i in range(n):
        city, state = STATES[i % len(STATES)]
        activated = rng.random() < 0.85
        sites.append({
            "id": f"SIT-{i + 1:03d}",
            "name": f"AIIA Collaborating Centre — {city}",
            "city": city,
            "state": state,
            "status": "activated" if activated else "planned",
            "activated_date": (DEMO_ANCHOR - timedelta(days=rng.randint(90, 480))).isoformat() if activated else None,
            "pi_name": PI_NAMES[i % len(PI_NAMES)],
            "capacity": rng.choice([20, 30, 40, 50, 60]),
            "study_ids": [],
        })
    return sites


def assign_pis_and_sites(studies, sites, rng):
    """Give each study a PI (drawn from site PIs) and 2-4 active sites.

    Also maintains the reverse mapping: Site.study_ids.
    """
    active = [s for s in sites if s["status"] == "activated"]
    pis = sorted({p for p in PI_NAMES})
    for i, study in enumerate(studies):
        k = min(rng.randint(2, 4), len(active))
        chosen = rng.sample(active, k)
        study["site_ids"] = [s["id"] for s in chosen]
        study["pi_id"] = pis[i % len(pis)]
        for s in chosen:
            if study["id"] not in s["study_ids"]:
                s["study_ids"].append(study["id"])


def make_milestones(study, rng):
    """The 8 lifecycle checkpoints, some hit, some planned, one slipping.

    Slippage rule: the first milestone whose planned date falls within 45 days of
    DEMO_ANCHOR but has no actual date becomes 'at_risk' — exactly one per study.
    """
    start = date.fromisoformat(study["start_date"])
    planned_offsets = [-90, -89, -30, -14, 60, 210, 260, 300]  # relative to start, days
    reached = LIFECYCLE.index(study["status"])
    at_risk_used = False
    milestones = []
    today = DEMO_ANCHOR
    for j, mtype in enumerate(MILESTONE_ORDER):
        planned = start + timedelta(days=planned_offsets[j])
        hit = j <= reached
        actual = planned - timedelta(days=rng.randint(-14, 21)) if hit else None
        if not hit:
            if not at_risk_used and planned <= today + timedelta(days=45):
                status = "at_risk"
                at_risk_used = True
            elif planned <= today:
                status = "missed"
            else:
                status = "planned"
        else:
            status = "achieved"
        milestones.append({
            "id": f"MS-{study['id']}-{j + 1:02d}",
            "study_id": study["id"],
            "type": mtype,
            "planned_date": planned.isoformat(),
            "actual_date": actual.isoformat() if actual else None,
            "status": status,
            "owner_role": MILESTONE_OWNERS[mtype],
        })
    return milestones
