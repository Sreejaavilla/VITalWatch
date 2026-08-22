"""Enrolment curves. OWNER: Roxy. The maths that makes the dashboard believable.

Expected curve: S-shaped (slow site activation, ramp, taper near target).
Actual curve: expected perturbed per site, with two studies pushed deliberately
below the lag threshold so the alert engine has real input.
"""


def expected_curve(target, start, end):
    raise NotImplementedError


def actual_curve(expected, lag_factor, rng):
    raise NotImplementedError


def make_subjects(study, sites, rng):
    """Pseudonymous subjects only — subject_code, never a name."""
    raise NotImplementedError
