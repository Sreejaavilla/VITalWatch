"""Visits, deviations, data queries and adverse events. OWNER: Roxy."""


def make_visits(subjects, rng):
    """Include some missed and some overdue, plus monitoring visits (some overdue)."""
    raise NotImplementedError


def make_deviations(subjects, rng):
    raise NotImplementedError


def make_queries(subjects, rng):
    """Open queries with realistic ageing so the query-ageing KPI is non-trivial."""
    raise NotImplementedError


def make_adverse_events(subjects, rng):
    """~50 AEs, 6 serious. Narratives in free text so Sreeja's coder has real input.
    Over-represent one term in one study arm so the DSMB view shows a signal."""
    raise NotImplementedError
