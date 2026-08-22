"""Enrolment curves. OWNER: Roxy. The maths that makes the dashboard believable.

Expected curve: S-shaped (slow site activation, ramp, taper near target).
Actual curve: expected perturbed per site, with two studies pushed deliberately
below the lag threshold so the alert engine has real input.

Every date derives from DEMO_ANCHOR (studies.py), never date.today(), so the
seed alone reproduces the whole dataset on any machine.
"""

import math
import random
from datetime import date

from datagen.generators.studies import DEMO_ANCHOR

# Story constants (datagen/README.md): STU-001 and STU-002 lag hard.
LAG_FACTORS = {"STU-001": 0.58, "STU-002": 0.67}
DEFAULT_LAG_RANGE = (0.62, 0.85)

SCREEN_FAILURE_RATE = 0.08


def expected_curve(target, start, end):
    """Planned cumulative enrolment, one point per day, logistic S-curve -> target."""
    start_d = _to_date(start)
    end_d = _to_date(end)
    days = max((end_d - start_d).days, 1)
    midpoint = days * 0.45  # ramp peaks a bit before the planned end
    steepness = 10.0 / days
    curve = []
    for d in range(days + 1):
        s = 1.0 / (1.0 + math.exp(-steepness * (d - midpoint)))
        curve.append(int(round(target * s)))
    curve[-1] = target
    return curve


def actual_curve(expected, lag_factor, rng, today_index=None):
    """Realised cumulative enrolment: expected perturbed by lag factor + noise.

    Monotonic non-decreasing, capped at target * lag_factor. If today_index is
    given, enrolment stops growing after that index (flatline) — that plateau is
    what makes a lagging study visibly lag on the chart.
    """
    ceiling = int(expected[-1] * min(lag_factor, 1.0))
    out = []
    prev = 0
    for i, v in enumerate(expected):
        if today_index is not None and i > today_index:
            out.append(prev)
            continue
        noise = rng.uniform(-0.02, 0.02) * max(expected[-1], 1) * min(1.0, i / 30)
        val = min(max(int(v * lag_factor + noise), prev), ceiling)
        out.append(val)
        prev = val
    return out


def make_subjects(study, sites, rng):
    """Pseudonymous subjects only — subject_code, never a name.

    Exactly study['actual_enrolment'] subjects, spread across the study's sites
    weighted by capacity (per the Site contract), ~8% screen failures.
    Consent is signed before screening, so every subject carries consent_version
    and consent_date — the contract makes them required for exactly that reason.
    age_band/sex are coarse enough for SDTM DM, too coarse to identify anyone.
    """
    n = study["actual_enrolment"]
    site_ids = list(study["site_ids"])
    capacities = {s["id"]: s.get("capacity", 1) for s in sites}
    weights = [max(capacities.get(sid, 1), 1) for sid in site_ids]
    total_w = sum(weights)
    arms = ["Arm A", "Arm B", "Placebo"] if study["phase"] != "observational" else ["cohort"]
    start = _to_date(study["start_date"])
    age_bands = ["18-30", "31-45", "46-60", "60+"]
    sexes = ["F", "M"]

    subjects = []
    n_failed_target = int(round(n * SCREEN_FAILURE_RATE))
    n_failed = 0
    # capacity-weighted site assignment without changing per-study sequence numbers
    expanded = [sid for sid, w in zip(site_ids, weights) for _ in range(max(round(n * w / total_w), 1))]
    for i in range(n):
        site_id = expanded[i % len(expanded)]
        screen_failed = n_failed < n_failed_target and rng.random() < SCREEN_FAILURE_RATE * 2
        if not screen_failed and (n - i) <= (n_failed_target - n_failed):
            # remaining slots must be failures to hit the rate exactly
            screen_failed = True
        if screen_failed:
            n_failed += 1
        seq = i + 1
        screened = start + timedelta_days(rng.randint(0, 30))
        enrolled = None if screen_failed else screened + timedelta_days(rng.randint(0, 7))
        status = "screen_failed" if screen_failed else rng.choice(
            ["enrolled", "enrolled", "completed"])
        subjects.append({
            "id": f"SUB-{study['id']}-{seq:04d}",
            "subject_code": f"{study['id']}-S-{seq:04d}",
            "study_id": study["id"],
            "site_id": site_id,
            "screened_date": screened.isoformat(),
            "enrolled_date": enrolled.isoformat() if enrolled else None,
            "status": status,
            "arm": None if screen_failed else rng.choice(arms),
            "age_band": rng.choice(age_bands),
            "sex": rng.choice(sexes),
            "consent_version": "v1.0",
            "consent_date": screened.isoformat(),
        })
    return subjects


def build_curves(studies, seed=1947):
    """Attach actual_enrolment to each study; return curves keyed by study id.

    Returns {study_id: {actual[], expected[], target}} for fixtures/enrolment.json.
    Mutates study dicts in place (actual_enrolment field).
    """
    curves = {}
    for study in studies:
        rng = random.Random(f"{seed}:{study['id']}")
        target = study["target_enrolment"]
        start = _to_date(study["start_date"])
        if study.get("end_date"):
            end = _to_date(study["end_date"])
        else:
            r = random.Random(f"{seed}:{study['id']}:end")
            end = max(start + timedelta_days(r.randint(430, 640)), _to_date(DEMO_ANCHOR) + timedelta_days(30))
        expected = expected_curve(target, start, end)
        # Planned end always lies beyond DEMO_ANCHOR (studies are ongoing), but
        # clamp defensively: today must index inside the curve.
        today_index = min(max((_to_date(DEMO_ANCHOR) - start).days, 0), len(expected) - 1)
        lag = LAG_FACTORS.get(study["id"], rng.uniform(*DEFAULT_LAG_RANGE))
        actual = actual_curve(expected, lag, rng, today_index=today_index)
        study["actual_enrolment"] = actual[today_index]
        curves[study["id"]] = {"actual": actual, "expected": expected, "target": target}
    return curves


def timedelta_days(n):
    from datetime import timedelta
    return timedelta(days=n)


def _to_date(value):
    return value if isinstance(value, date) else date.fromisoformat(value)
