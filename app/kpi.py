"""KPI computation — read-only, straight from SQLite.

Nothing here is cached or stored. Every number is derived on request, so editing a row
in the database with `sqlite3` and refreshing the page changes the figure. That is the
answer to "are these numbers real or are they hardcoded?", and it is worth being able
to demonstrate rather than assert.

Definitions matter more than the arithmetic. Each metric below states what it counts,
because "open queries" and "overdue visits" are exactly the kind of thing two people
will define differently and then disagree about on stage.
"""

from __future__ import annotations

from .db import Connection  # driver-neutral: SQLite or Postgres
from datetime import date

from . import db
from .config import settings
from .datagen import TODAY
from .models import PortfolioKPI, StudyKPI, utcnow

#: A study counts as active once it has ethics approval and before it closes out.
#: Protocol-stage and closed-out studies are real portfolio entries but nobody is
#: enrolling into them, so counting them would flatter the enrolment figures.
ACTIVE_STATUSES = (
    "ec_approval", "ctri_registered", "site_activation", "screening", "enrolling", "follow_up",
)

#: An SAE stays open until the subject has recovered or the outcome is final.
OPEN_SAE_OUTCOMES = ("recovering", "not_recovered", "unknown")

#: Planned enrolment duration, in days, from first-subject-in to last-subject-in.
#: Used to work out where a study *should* be today. Matches datagen's milestone plan.
ENROLMENT_WINDOW_DAYS = 400


def expected_enrolment(start_date: str, target: int, today: date | None = None) -> int:
    """Where the straight-line plan says a study should be by `today`.

    Public because three screens read it — the study page, the portfolio table and the
    investigation's recruitment evidence — and three copies of a plan curve is three
    chances for two screens to quote different numbers for the same study.
    """
    elapsed = ((today or _today()) - date.fromisoformat(start_date)).days
    return int(target * min(max(elapsed / ENROLMENT_WINDOW_DAYS, 0.0), 1.0))


def _today() -> date:
    """The demo's 'today'.

    Pinned to the generator's reference date so the seeded portfolio keeps telling the
    same story — an SAE seeded as breached stays breached next week. Swap this for
    `date.today()` the moment real data arrives.
    """
    return TODAY


def _scalar(conn: Connection, sql: str, params: tuple = ()) -> int:
    return conn.execute(sql, params).fetchone()[0] or 0


# ------------------------------------------------------------------ shared pieces


def _open_queries(conn: Connection, study_id: str | None = None) -> int:
    """Queries raised and not yet closed. An answered-but-not-closed query is still open —
    someone still has to accept the answer."""
    where = "status != 'closed'"
    if study_id:
        return _scalar(conn, f"SELECT COUNT(*) FROM queries WHERE {where} AND study_id = ?", (study_id,))
    return _scalar(conn, f"SELECT COUNT(*) FROM queries WHERE {where}")


def _overdue_monitoring_visits(conn: Connection, study_id: str | None = None) -> int:
    """Monitoring visits that are outstanding, on either of two counts:

    * scheduled more than `monitoring_overdue_days` ago and never conducted, or
    * conducted, but the monitoring report was never filed.

    The second case is the one site staff forget. A visit that happened but produced no
    report is not evidence of oversight.
    """
    cutoff = (_today() - _td(settings.monitoring_overdue_days)).isoformat()
    sql = """
        SELECT COUNT(*) FROM visits
         WHERE monitoring_visit = 1
           AND ( (actual_date IS NULL AND scheduled_date < ?)
                 OR (actual_date IS NOT NULL AND report_filed = 0) )
    """
    if study_id:
        return _scalar(conn, sql + " AND study_id = ?", (cutoff, study_id))
    return _scalar(conn, sql, (cutoff,))


def _open_saes(conn: Connection, study_id: str | None = None) -> int:
    placeholders = ",".join("?" * len(OPEN_SAE_OUTCOMES))
    sql = f"SELECT COUNT(*) FROM adverse_events WHERE serious = 1 AND outcome IN ({placeholders})"
    if study_id:
        return _scalar(conn, sql + " AND study_id = ?", (*OPEN_SAE_OUTCOMES, study_id))
    return _scalar(conn, sql, OPEN_SAE_OUTCOMES)


def _td(days: int):
    from datetime import timedelta

    return timedelta(days=days)


# --------------------------------------------------------------------- portfolio


def portfolio_kpi(conn: Connection) -> PortfolioKPI:
    """The six headline numbers, plus the two totals they are read against."""
    placeholders = ",".join("?" * len(ACTIVE_STATUSES))
    active = conn.execute(
        f"""SELECT COUNT(*) AS n,
                   COALESCE(SUM(actual_enrolment), 0) AS enrolled,
                   COALESCE(SUM(target_enrolment), 0) AS target
              FROM studies WHERE status IN ({placeholders})""",
        ACTIVE_STATUSES,
    ).fetchone()
    sites = conn.execute(
        # CASE rather than SUM(status = 'activated'): Postgres will not sum a boolean.
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN status = 'activated' THEN 1 ELSE 0 END) AS activated FROM sites"
    ).fetchone()

    return PortfolioKPI(
        generated_at=utcnow(),
        active_studies=active["n"],
        enrolled_total=active["enrolled"],
        target_total=active["target"],
        sites_activated=sites["activated"] or 0,
        sites_total=sites["total"],
        open_queries=_open_queries(conn),
        overdue_monitoring_visits=_overdue_monitoring_visits(conn),
        open_saes=_open_saes(conn),
    )


# ------------------------------------------------------------------------- study


def study_kpi(conn: Connection, study_id: str) -> StudyKPI | None:
    """Per-study drill-down. Returns None if the study does not exist."""
    study = conn.execute("SELECT * FROM studies WHERE id = ?", (study_id,)).fetchone()
    if study is None:
        return None

    today = _today()
    target = study["target_enrolment"]
    enrolled = study["actual_enrolment"]

    # Where the plan says enrolment should be by now — a straight line from study start
    # across the enrolment window. Crude, and honest about being crude: the gap between
    # this and `enrolled` is what drives the enrolment-lag alert.
    expected = expected_enrolment(study["start_date"], target, today)

    screened = _scalar(conn, "SELECT COUNT(*) FROM subjects WHERE study_id = ?", (study_id,))
    failed = _scalar(
        conn, "SELECT COUNT(*) FROM subjects WHERE study_id = ? AND status = 'screen_failed'", (study_id,)
    )

    # Visit compliance counts only subject visits that were due by today. Upcoming
    # visits are not yet compliant or non-compliant, and including them would make a
    # study look worse the more of it remains.
    due = _scalar(
        conn,
        "SELECT COUNT(*) FROM visits WHERE study_id = ? AND monitoring_visit = 0 AND scheduled_date <= ?",
        (study_id, today.isoformat()),
    )
    completed = _scalar(
        conn,
        """SELECT COUNT(*) FROM visits
            WHERE study_id = ? AND monitoring_visit = 0 AND scheduled_date <= ? AND status = 'completed'""",
        (study_id, today.isoformat()),
    )

    ageing = conn.execute(
        f"SELECT AVG({db.days_between('?', 'raised_date')}) FROM queries "
        "WHERE study_id = ? AND status != 'closed'",
        (today.isoformat(), study_id),
    ).fetchone()[0]
    # Postgres AVG returns Decimal; float() keeps the value the same shape on both engines.
    ageing = float(ageing) if ageing is not None else None

    deviations = _scalar(conn, "SELECT COUNT(*) FROM deviations WHERE study_id = ?", (study_id,))
    site_count = _scalar(conn, "SELECT COUNT(*) FROM study_sites WHERE study_id = ?", (study_id,))

    nxt = conn.execute(
        """SELECT type, planned_date FROM milestones
            WHERE study_id = ? AND actual_date IS NULL AND planned_date >= ?
            ORDER BY planned_date ASC LIMIT 1""",
        (study_id, today.isoformat()),
    ).fetchone()

    return StudyKPI(
        generated_at=utcnow(),
        study_id=study_id,
        enrolment_pct=0.0 if target == 0 else round(100.0 * enrolled / target, 1),
        enrolled=enrolled,
        target=target,
        expected_by_today=expected,
        screen_failure_rate=0.0 if screened == 0 else round(100.0 * failed / screened, 1),
        visit_compliance_pct=0.0 if due == 0 else round(100.0 * completed / due, 1),
        open_queries=_open_queries(conn, study_id),
        open_query_ageing_days=round(ageing or 0.0, 1),
        deviation_rate_per_site=0.0 if site_count == 0 else round(deviations / site_count, 1),
        open_saes=_open_saes(conn, study_id),
        days_to_next_milestone=(date.fromisoformat(nxt["planned_date"]) - today).days if nxt else None,
        # Raw enum value; the `label` filter spells it the way the domain does.
        next_milestone=nxt["type"] if nxt else None,
    )
