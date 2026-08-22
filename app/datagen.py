"""Synthetic portfolio generator.

Everything in this system is invented. No real patient, no real trial, no real AIIA
record touches this codebase — that is the point, and it is why the footer says so on
every page.

The generator is seeded from `settings.seed_random_seed`, so the portfolio is identical
on every run. That matters twice: the demo script can name a specific study, and a
regenerated database matches the screenshots in the deck.

The data is shaped to make the dashboard say something. Some studies enrol ahead of
plan and some behind; one is enrolling without a CTRI number; one ethics approval
expires inside the renewal window; some monitoring visits are overdue; some SAEs are
past their 24-hour clock. A portfolio where nothing is wrong demonstrates nothing.
"""

from __future__ import annotations

import random
import sqlite3
import uuid
from datetime import date, datetime, time, timedelta, timezone

from . import audit, pv
from .config import settings

TODAY = date(2026, 8, 22)

THERAPEUTIC_AREAS = [
    ("Rheumatology", "Amavata (Rheumatoid Arthritis)"),
    ("Metabolic", "Madhumeha (Type 2 Diabetes Mellitus)"),
    ("Respiratory", "Tamaka Shwasa (Bronchial Asthma)"),
    ("Dermatology", "Kitibha (Plaque Psoriasis)"),
    ("Gastroenterology", "Grahani (Irritable Bowel Syndrome)"),
    ("Hepatology", "Yakrit Roga (Non-Alcoholic Fatty Liver)"),
    ("Neurology", "Anidra (Primary Insomnia)"),
    ("Cardiology", "Hridroga (Dyslipidaemia)"),
]

FORMULATIONS = [
    "Guduchi Ghana Vati", "Ashwagandha Churna", "Triphala Guggulu", "Punarnava Mandur",
    "Shirishadi Kwatha", "Kutajarishta", "Arjuna Ksheerapaka", "Yashtimadhu Ghrita",
]

SITES = [
    ("All India Institute of Ayurveda", "New Delhi", "Delhi", 120),
    ("National Institute of Ayurveda", "Jaipur", "Rajasthan", 90),
    ("Government Ayurveda College", "Thiruvananthapuram", "Kerala", 80),
    ("IPGT&RA, Gujarat Ayurved University", "Jamnagar", "Gujarat", 75),
    ("Ayurveda Mahavidyalaya", "Pune", "Maharashtra", 60),
    ("Regional Ayurveda Research Institute", "Guwahati", "Assam", 45),
    ("Government Ayurveda Medical College", "Bengaluru", "Karnataka", 70),
    ("Shri Dhanwantry Ayurvedic College", "Chandigarh", "Punjab", 50),
    ("State Ayurvedic College", "Lucknow", "Uttar Pradesh", 65),
    ("Ayurveda Regional Research Institute", "Bhubaneswar", "Odisha", 40),
    ("Government Ayurveda College", "Nagpur", "Maharashtra", 55),
    ("North Eastern Institute of Ayurveda", "Shillong", "Meghalaya", 35),
]

PI_NAMES = [
    "Dr. R. Krishnan", "Dr. S. Deshpande", "Dr. A. Nair", "Dr. M. Bhattacharya",
    "Dr. P. Iyer", "Dr. V. Sharma", "Dr. K. Menon", "Dr. T. Rao",
    "Dr. N. Chatterjee", "Dr. L. Pillai", "Dr. G. Kulkarni", "Dr. H. Joshi",
]


DEVIATION_CATEGORIES = [
    ("Visit window", "Follow-up visit conducted outside the protocol-defined window", "minor"),
    ("Consent", "Consent re-signed on the amended version after the first dose", "major"),
    ("Eligibility", "Subject enrolled with a haemoglobin value below the inclusion threshold", "critical"),
    ("Study drug", "Dispensing log entry missing for one subject-visit", "minor"),
    ("Procedure", "Scheduled laboratory sample not collected at the week-8 visit", "major"),
    ("Documentation", "Source document not signed by the investigator within the required period", "minor"),
]

QUERY_FIELDS = [
    ("SYSBP", "Systolic BP recorded as 220 mmHg — please confirm or correct."),
    ("AESTDAT", "Adverse event start date precedes the informed consent date."),
    ("VISITDAT", "Visit date is after the date of the following visit. Please clarify."),
    ("CONMED", "Concomitant medication recorded with no start date."),
    ("HGB", "Haemoglobin value outside the physiological range. Confirm the unit."),
    ("WEIGHT", "Weight differs by 14 kg from the previous visit. Please verify."),
]

QUERY_RAISERS = ["dm.aiia", "monitor.north", "monitor.south", "dm.npvcc"]


def _dt(d: date, hour: int = 9, minute: int = 0) -> str:
    return datetime.combine(d, time(hour, minute), tzinfo=timezone.utc).isoformat()


def _id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:03d}"


def seed(conn: sqlite3.Connection) -> None:
    """Populate an empty database. Called from `db.init` on startup."""
    rng = random.Random(settings.seed_random_seed)

    sites = _seed_sites(conn, rng)
    studies = _seed_studies(conn, rng, sites)
    _seed_milestones(conn, rng, studies)
    subjects = _seed_subjects(conn, rng, studies)
    _seed_visits(conn, rng, studies, subjects)
    _seed_deviations(conn, rng, studies, subjects)
    _seed_queries(conn, rng, studies, subjects)
    _seed_adverse_events(conn, rng, studies, subjects)
    _seed_audit(conn, studies)
    conn.commit()


# ------------------------------------------------------------------------- sites


def _seed_sites(conn: sqlite3.Connection, rng: random.Random) -> list[dict]:
    rows = []
    for i, (name, city, state, capacity) in enumerate(SITES, start=1):
        # Two sites are still being brought up — "sites activated" should never read n/n,
        # because a portfolio where every site is live has nothing to manage.
        activated = i <= len(SITES) - 2
        row = {
            "id": _id("SITE", i),
            "name": name,
            "city": city,
            "state": state,
            "status": "activated" if activated else "planned",
            "activated_date": (TODAY - timedelta(days=rng.randint(200, 600))).isoformat()
            if activated else None,
            "pi_name": PI_NAMES[i - 1],
            "capacity": capacity,
        }
        conn.execute(
            """INSERT INTO sites (id, name, city, state, status, activated_date, pi_name, capacity)
               VALUES (:id,:name,:city,:state,:status,:activated_date,:pi_name,:capacity)""",
            row,
        )
        rows.append(row)
    return rows


# ------------------------------------------------------------------------ studies


def _seed_studies(conn: sqlite3.Connection, rng: random.Random, sites: list[dict]) -> list[dict]:
    active_sites = [s for s in sites if s["status"] == "activated"]
    statuses = [
        "enrolling", "enrolling", "enrolling", "enrolling",
        "follow_up", "screening", "ctri_registered", "close_out",
    ]
    phases = ["II", "III", "II", "observational", "III", "II", "IV", "III"]
    rows: list[dict] = []

    for i in range(1, settings.seed_studies + 1):
        area, title = THERAPEUTIC_AREAS[(i - 1) % len(THERAPEUTIC_AREAS)]
        status = statuses[(i - 1) % len(statuses)]
        started = TODAY - timedelta(days=rng.randint(120, 700))
        target = rng.choice([40, 50, 60, 70, 90, 110])

        # Study 3 enrols without a CTRI number. Prospective registration is mandatory,
        # so this is a finding the portfolio is supposed to surface, not an oversight.
        registered = not (i == 3)
        ec_approval = started - timedelta(days=rng.randint(30, 90))

        # Study 2's ethics approval expires inside the renewal window, so the EC-renewal
        # alert has something real to fire on.
        if i == 2:
            ec_expiry = TODAY + timedelta(days=21)
        elif status == "close_out":
            ec_expiry = TODAY + timedelta(days=rng.randint(200, 400))
        else:
            ec_expiry = ec_approval + timedelta(days=365 * rng.randint(2, 3))

        # Enrolment fraction, deliberately mixed: studies 1 and 5 run behind plan.
        fraction = {1: 0.34, 5: 0.41}.get(i, rng.uniform(0.62, 0.95))
        if status in ("ctri_registered", "screening"):
            fraction = rng.uniform(0.0, 0.08)
        if status == "close_out":
            fraction = 1.0

        study_sites = rng.sample(active_sites, rng.randint(2, min(4, len(active_sites))))
        row = {
            "id": _id("STU", i),
            "title": f"{title} — {rng.choice(FORMULATIONS)}",
            "protocol_no": f"AIIA/CTP/{2024 + (i % 3)}/{i:02d}",
            "ctri_number": f"CTRI/{started.year}/{rng.randint(1,12):02d}/{rng.randint(100000,999999)}"
            if registered else None,
            "phase": phases[(i - 1) % len(phases)],
            "status": status,
            "therapeutic_area": area,
            "ec_approval_date": ec_approval.isoformat(),
            "ec_expiry_date": ec_expiry.isoformat(),
            "ctri_registration_date": (started - timedelta(days=rng.randint(5, 25))).isoformat()
            if registered else None,
            "target_enrolment": target,
            "actual_enrolment": int(target * fraction),
            "pi_name": rng.choice(PI_NAMES),
            "start_date": started.isoformat(),
            "end_date": None,
        }
        conn.execute(
            """INSERT INTO studies
               (id, title, protocol_no, ctri_number, phase, status, therapeutic_area,
                ec_approval_date, ec_expiry_date, ctri_registration_date,
                target_enrolment, actual_enrolment, pi_name, start_date, end_date)
               VALUES (:id,:title,:protocol_no,:ctri_number,:phase,:status,:therapeutic_area,
                       :ec_approval_date,:ec_expiry_date,:ctri_registration_date,
                       :target_enrolment,:actual_enrolment,:pi_name,:start_date,:end_date)""",
            row,
        )
        for site in study_sites:
            conn.execute(
                "INSERT INTO study_sites (study_id, site_id) VALUES (?,?)", (row["id"], site["id"])
            )
        row["site_ids"] = [s["id"] for s in study_sites]
        rows.append(row)
    return rows


# --------------------------------------------------------------------- milestones

MILESTONE_PLAN = [
    ("ec_approval", -60),
    ("ctri_registration", -20),
    ("first_site_activated", 10),
    ("first_subject_in", 30),
    ("fifty_pct_enrolled", 180),
    ("last_subject_in", 400),
    ("database_lock", 480),
    ("close_out", 540),
]


def _seed_milestones(conn: sqlite3.Connection, rng: random.Random, studies: list[dict]) -> None:
    for study in studies:
        started = date.fromisoformat(study["start_date"])
        for n, (mtype, offset) in enumerate(MILESTONE_PLAN, start=1):
            planned = started + timedelta(days=offset)
            if planned <= TODAY:
                # A milestone in the past is either done or missed. Most are done.
                achieved = rng.random() < 0.82
                actual = (planned + timedelta(days=rng.randint(-5, 20))).isoformat() if achieved else None
                status = "achieved" if achieved else "missed"
            else:
                actual = None
                # Due inside 45 days with the study behind plan reads as at risk.
                status = "at_risk" if (planned - TODAY).days < 45 and rng.random() < 0.4 else "planned"
            conn.execute(
                """INSERT INTO milestones (id, study_id, type, planned_date, actual_date, status)
                   VALUES (?,?,?,?,?,?)""",
                (f"{study['id']}-MS-{n:02d}", study["id"], mtype, planned.isoformat(), actual, status),
            )


# ----------------------------------------------------------------------- subjects


def _seed_subjects(conn: sqlite3.Connection, rng: random.Random, studies: list[dict]) -> list[dict]:
    age_bands = ["18-29", "30-39", "40-49", "50-59", "60-69", "70+"]
    rows: list[dict] = []

    for study in studies:
        enrolled_target = study["actual_enrolment"]
        if not enrolled_target:
            continue
        # Roughly one in five screened subjects screen-fails — a realistic ratio, and the
        # screen-failure-rate KPI needs failures to be non-trivial.
        screened_total = int(enrolled_target * rng.uniform(1.15, 1.35)) + 1
        started = date.fromisoformat(study["start_date"])
        span = max((TODAY - started).days, 30)

        for n in range(1, screened_total + 1):
            site_id = study["site_ids"][n % len(study["site_ids"])]
            screened = started + timedelta(days=rng.randint(20, span))
            enrolled = n <= enrolled_target
            if enrolled:
                status = rng.choices(
                    ["enrolled", "completed", "withdrawn"], weights=[70, 22, 8]
                )[0]
            else:
                status = "screen_failed"
            row = {
                "id": str(uuid.uuid4()),
                "subject_code": f"{study['id'].replace('STU', 'AIIA')}-{n:03d}",
                "study_id": study["id"],
                "site_id": site_id,
                "screened_date": screened.isoformat(),
                "enrolled_date": (screened + timedelta(days=rng.randint(1, 14))).isoformat()
                if enrolled else None,
                "status": status,
                "arm": rng.choice(["Trial drug", "Control"]) if enrolled else None,
                "age_band": rng.choice(age_bands),
                "sex": rng.choice(["M", "F"]),
                "consent_version": f"v{rng.randint(1,3)}.0",
                "consent_date": screened.isoformat(),
            }
            conn.execute(
                """INSERT INTO subjects
                   (id, subject_code, study_id, site_id, screened_date, enrolled_date,
                    status, arm, age_band, sex, consent_version, consent_date)
                   VALUES (:id,:subject_code,:study_id,:site_id,:screened_date,:enrolled_date,
                           :status,:arm,:age_band,:sex,:consent_version,:consent_date)""",
                row,
            )
            rows.append(row)
    return rows


# ------------------------------------------------------------------------- visits

VISIT_SCHEDULE = [("Screening", 0), ("Baseline", 14), ("Week 4", 42), ("Week 8", 70), ("Week 12", 98)]


def _seed_visits(
    conn: sqlite3.Connection, rng: random.Random, studies: list[dict], subjects: list[dict]
) -> None:
    # Subject visits.
    for subject in subjects:
        if subject["status"] == "screen_failed":
            continue
        anchor = date.fromisoformat(subject["enrolled_date"] or subject["screened_date"])
        for name, offset in VISIT_SCHEDULE:
            scheduled = anchor + timedelta(days=offset)
            if scheduled > TODAY:
                status, actual = "upcoming", None
            elif rng.random() < 0.90:
                status = "completed"
                actual = (scheduled + timedelta(days=rng.randint(-2, 5))).isoformat()
            elif (TODAY - scheduled).days > 14:
                status, actual = "missed", None
            else:
                status, actual = "overdue", None
            conn.execute(
                """INSERT INTO visits
                   (id, study_id, site_id, subject_code, visit_name, scheduled_date,
                    actual_date, window_days, status, monitoring_visit, report_filed)
                   VALUES (?,?,?,?,?,?,?,?,?,0,0)""",
                (
                    str(uuid.uuid4()), subject["study_id"], subject["site_id"],
                    subject["subject_code"], name, scheduled.isoformat(), actual, 7, status,
                ),
            )

    # Site monitoring visits — quarterly per study-site. These drive the overdue alert,
    # and a visit conducted but with no report filed still counts as outstanding.
    #
    # Historical visits are essentially all completed, because a portfolio where a
    # quarter of all monitoring never happened is not a dashboard finding, it is a
    # broken institution — and an alert that fires on every study is one nobody reads.
    # Exactly three studies carry a genuinely missed visit, planted below.
    for study in studies:
        started = date.fromisoformat(study["start_date"])
        for site_id in study["site_ids"]:
            scheduled = started + timedelta(days=90)
            n = 1
            while scheduled <= TODAY + timedelta(days=90):
                if scheduled > TODAY:
                    status, actual, filed = "upcoming", None, 0
                else:
                    status = "completed"
                    actual = (scheduled + timedelta(days=rng.randint(0, 6))).isoformat()
                    # A visit that happened but produced no report is still outstanding.
                    filed = 1 if rng.random() < 0.88 else 0
                conn.execute(
                    """INSERT INTO visits
                       (id, study_id, site_id, subject_code, visit_name, scheduled_date,
                        actual_date, window_days, status, monitoring_visit, report_filed)
                       VALUES (?,?,?,?,?,?,?,?,?,1,?)""",
                    (
                        str(uuid.uuid4()), study["id"], site_id, None,
                        f"Monitoring visit {n}", scheduled.isoformat(), actual, 14, status, filed,
                    ),
                )
                scheduled += timedelta(days=90)
                n += 1

    _plant_overdue_monitoring(conn, studies)


#: Studies given a genuinely missed monitoring visit, so the overdue rule has exactly
#: three things to fire on rather than forty.
OVERDUE_MONITORING_STUDIES = {"STU-002": 47, "STU-004": 96, "STU-005": 21}


def _plant_overdue_monitoring(conn: sqlite3.Connection, studies: list[dict]) -> None:
    """Give three studies one overdue monitoring visit each, at known ages.

    Planted rather than left to chance: the demo script names these studies, and a
    generator that sometimes produces four and sometimes none makes the script a lie.
    The ages straddle the 90-day mark so both severity levels of the rule are visible.
    """
    by_id = {s["id"]: s for s in studies}
    for study_id, days_late in OVERDUE_MONITORING_STUDIES.items():
        study = by_id.get(study_id)
        if not study:
            continue
        scheduled = TODAY - timedelta(days=days_late)
        conn.execute(
            """INSERT INTO visits
               (id, study_id, site_id, subject_code, visit_name, scheduled_date,
                actual_date, window_days, status, monitoring_visit, report_filed)
               VALUES (?,?,?,NULL,?,?,NULL,14,'overdue',1,0)""",
            (
                str(uuid.uuid4()), study_id, study["site_ids"][0],
                "Monitoring visit (not conducted)", scheduled.isoformat(),
            ),
        )


# --------------------------------------------------------------------- deviations


def _seed_deviations(
    conn: sqlite3.Connection, rng: random.Random, studies: list[dict], subjects: list[dict]
) -> None:
    by_study: dict[str, list[dict]] = {}
    for s in subjects:
        by_study.setdefault(s["study_id"], []).append(s)

    for study in studies:
        pool = by_study.get(study["id"], [])
        if not pool:
            continue
        for _ in range(rng.randint(2, 9)):
            category, description, severity = rng.choice(DEVIATION_CATEGORIES)
            subject = rng.choice(pool)
            detected = date.fromisoformat(subject["screened_date"]) + timedelta(days=rng.randint(5, 90))
            if detected > TODAY:
                detected = TODAY - timedelta(days=rng.randint(1, 30))
            # Major and critical deviations are reportable to the EC. Some have not been
            # reported — that gap is the whole reason the dashboard shows this column.
            reportable = severity in ("major", "critical")
            reported = reportable and rng.random() < 0.7
            conn.execute(
                """INSERT INTO deviations
                   (id, study_id, site_id, subject_code, category, description,
                    detected_date, severity, reported_to_ec, reported_date, resolution)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()), study["id"], subject["site_id"], subject["subject_code"],
                    category, description, detected.isoformat(), severity,
                    1 if reported else 0,
                    (detected + timedelta(days=rng.randint(1, 5))).isoformat() if reported else None,
                    "Retrained site staff; corrective action documented." if rng.random() < 0.5 else None,
                ),
            )


# ------------------------------------------------------------------------ queries


def _seed_queries(
    conn: sqlite3.Connection, rng: random.Random, studies: list[dict], subjects: list[dict]
) -> None:
    by_study: dict[str, list[dict]] = {}
    for s in subjects:
        by_study.setdefault(s["study_id"], []).append(s)

    for study in studies:
        pool = by_study.get(study["id"], [])
        if not pool:
            continue
        for _ in range(rng.randint(4, 16)):
            field, question = rng.choice(QUERY_FIELDS)
            subject = rng.choice(pool)
            # Some queries are deliberately old — open-query ageing is a KPI and needs a tail.
            raised = TODAY - timedelta(days=rng.choice([2, 5, 9, 14, 21, 30, 45, 62, 91]))
            status = rng.choices(["open", "answered", "closed"], weights=[35, 20, 45])[0]
            answered = raised + timedelta(days=rng.randint(1, 8)) if status in ("answered", "closed") else None
            closed = answered + timedelta(days=rng.randint(1, 6)) if status == "closed" and answered else None
            conn.execute(
                """INSERT INTO queries
                   (id, study_id, site_id, subject_code, field, question,
                    raised_date, raised_by, answered_date, closed_date, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()), study["id"], subject["site_id"], subject["subject_code"],
                    field, question, raised.isoformat(), rng.choice(QUERY_RAISERS),
                    answered.isoformat() if answered else None,
                    closed.isoformat() if closed else None, status,
                ),
            )


# ----------------------------------------------------------------- adverse events


#: Non-serious narratives. Deliberately written the way site staff actually write them —
#: "loose stools", not "diarrhoea" — because coding free text is the point of app/pv.py.
AE_ROUTINE = [
    ("mild headache reported on day 3, resolved without treatment", "mild"),
    ("nausea after morning dose, settled within two hours", "mild"),
    ("loose stools for two days, subject continued on study drug", "mild"),
    ("mild body ache after the evening dose", "mild"),
    ("gastric discomfort after evening dose", "moderate"),
    ("dizziness on standing, blood pressure recorded as normal", "moderate"),
    ("elevated liver enzymes on routine labs, repeat scheduled", "moderate"),
    ("generalised skin rash, antihistamine started", "moderate"),
    ("difficulty sleeping through the night since week 2", "mild"),
    ("tiredness through the day, no other complaint", "mild"),
    ("joint pains in both knees, unchanged from baseline", "moderate"),
    ("dry cough at night, no fever", "mild"),
]

#: Serious events. Six of these are seeded, no more — an SAE rate of one in eight would
#: itself be the headline finding, and would drown the ones that matter.
AE_SERIOUS = [
    ("severe abdominal pain, subject hospitalised for observation", "severe", "not_recovered"),
    ("acute urticaria with facial swelling, emergency admission", "severe", "recovering"),
    ("syncopal episode at home, admitted overnight", "severe", "recovered"),
    ("jaundice with raised bilirubin, study drug withdrawn", "severe", "not_recovered"),
    ("breathlessness on exertion, admitted for evaluation", "severe", "recovering"),
    ("severe vomiting with dehydration, intravenous fluids given", "severe", "recovered"),
]

#: The safety signal. One study reports the same skin reaction far more often than the
#: rest of the portfolio — which is invisible in free text and obvious once coded, and
#: is exactly what the DSMB view exists to surface.
SIGNAL_STUDY = "STU-004"
SIGNAL_NARRATIVES = [
    "itching over both forearms, topical relief given",
    "itchy skin over the arms after the morning dose",
    "persistent itching on the forearms, no rash seen",
    "pruritus of both arms reported at the week 4 visit",
    "itching over forearms and neck, settled overnight",
    "complains of itch over the arms since starting study drug",
    "itching over both forearms again this week",
]


def _insert_ae(
    conn: sqlite3.Connection, rng: random.Random, study: dict, subject: dict,
    narrative: str, severity: str, serious: bool, outcome: str | None = None,
    reported_hours_ago: float | None = None,
) -> None:
    now = datetime.combine(TODAY, time(12, 0), tzinfo=timezone.utc)

    if reported_hours_ago is not None:
        # Serious events get an exact reporting time, because the 24-hour clock state is
        # what the demo shows and it must not depend on a dice roll.
        reported = now - timedelta(hours=reported_hours_ago)
        onset = reported.date() - timedelta(days=rng.randint(0, 1))
    else:
        onset = TODAY - timedelta(days=rng.randint(1, 120))
        # Reported some hours after onset — the gap is why a clock can already be
        # breached at the moment the event is entered.
        reported = datetime.combine(
            onset, time(rng.randint(8, 20), rng.choice([0, 15, 30, 45])), tzinfo=timezone.utc
        ) + timedelta(hours=rng.randint(1, 30))

    deadline_24h = deadline_14d = None
    timeline_status = "not_applicable"
    if serious:
        deadline_24h = reported + timedelta(hours=settings.sae_initial_report_hours)
        deadline_14d = reported + timedelta(days=settings.sae_narrative_days)
        hours_left = (deadline_24h - now).total_seconds() / 3600
        timeline_status = (
            "breached" if hours_left < 0
            else "due_soon" if hours_left < settings.sae_due_soon_hours
            else "on_track"
        )

    conn.execute(
        """INSERT INTO adverse_events
           (id, study_id, site_id, subject_code, narrative, onset_date, serious,
            severity, causality, outcome, coded_term, coded_code, coding_confidence,
            coding_source, suspect_drug, drug_code, drug_coding_source,
            reported_at, deadline_24h, deadline_14d, timeline_status)
           VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,NULL,'uncoded',?,NULL,'uncoded',?,?,?,?)""",
        (
            str(uuid.uuid4()), study["id"], subject["site_id"], subject["subject_code"],
            narrative, onset.isoformat(), 1 if serious else 0, severity,
            rng.choices(
                ["unrelated", "unlikely", "possible", "probable", "certain"],
                weights=[20, 20, 35, 20, 5],
            )[0],
            outcome or rng.choices(
                ["recovered", "recovering", "not_recovered", "recovered_with_sequelae", "unknown"],
                weights=[55, 20, 12, 8, 5],
            )[0],
            study["title"].split("—")[-1].strip(),
            reported.isoformat(),
            deadline_24h.isoformat() if deadline_24h else None,
            deadline_14d.isoformat() if deadline_14d else None,
            timeline_status,
        ),
    )


def _seed_adverse_events(
    conn: sqlite3.Connection, rng: random.Random, studies: list[dict], subjects: list[dict]
) -> None:
    """Around fifty events: routine ones spread across the portfolio, six serious ones,
    and one clustered term in a single study."""
    by_study: dict[str, list[dict]] = {}
    for s in subjects:
        if s["status"] != "screen_failed":
            by_study.setdefault(s["study_id"], []).append(s)

    # Routine events, spread across every study that has enrolled anyone.
    for study in studies:
        pool = by_study.get(study["id"], [])
        if not pool:
            continue
        for _ in range(rng.randint(2, 6)):
            narrative, severity = rng.choice(AE_ROUTINE)
            _insert_ae(conn, rng, study, rng.choice(pool), narrative, severity, serious=False)

    # The clustered skin reaction. Same study, same term, seven times.
    signal_study = next((s for s in studies if s["id"] == SIGNAL_STUDY), None)
    signal_pool = by_study.get(SIGNAL_STUDY, [])
    if signal_study and signal_pool:
        for narrative in SIGNAL_NARRATIVES:
            _insert_ae(
                conn, rng, signal_study, rng.choice(signal_pool), narrative, "mild", serious=False
            )

    # Six serious events, at fixed reporting times relative to the demo clock. Two are
    # already past their 24-hour deadline, one is inside the final hours, three are on
    # track — so the AE screen shows all three clock states at once, and nobody has to
    # wait for a countdown to run down on stage.
    hours_ago = [216, 30, 20, 8, 3, 1]  # breached, breached, due soon, then on track
    eligible = [s for s in studies if by_study.get(s["id"])]
    for (narrative, severity, outcome), reported_hours_ago in zip(AE_SERIOUS, hours_ago):
        study = rng.choice(eligible)
        _insert_ae(
            conn, rng, study, rng.choice(by_study[study["id"]]), narrative, severity,
            serious=True, outcome=outcome, reported_hours_ago=reported_hours_ago,
        )

    # Code every narrative against the curated vocabulary. Done here rather than left to
    # the UI so the portfolio arrives already aggregable — an AE table full of "Uncoded"
    # is a screen that cannot answer a safety question.
    coded = pv.code_uncoded_events(conn, commit=False)
    total = conn.execute("SELECT COUNT(*) FROM adverse_events").fetchone()[0]
    print(f"[datagen] coded {coded}/{total} adverse events against app/terms.csv")


# -------------------------------------------------------------------------- audit


def _seed_audit(conn: sqlite3.Connection, studies: list[dict]) -> None:
    """Lay down a short prior history so the chain is not empty at demo time.

    Timestamps are back-dated to each study's start; the seeder is the only caller ever
    allowed to pass a timestamp (see `audit.record`).
    """
    for study in studies:
        audit.record(
            conn,
            actor="system.seed",
            action="create",
            resource_type="study",
            resource_id=study["id"],
            after={
                "id": study["id"],
                "title": study["title"],
                "protocol_no": study["protocol_no"],
                "status": study["status"],
                "target_enrolment": study["target_enrolment"],
            },
            reason="Synthetic portfolio generated for demonstration. No real trial data.",
            timestamp=_dt(date.fromisoformat(study["start_date"])),
            commit=False,
        )
