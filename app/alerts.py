"""Alert rules.

Three rules, each reading its threshold from `config.py` and therefore from the
environment. That is deliberate and worth demonstrating: change `ENROLMENT_LAG_PCT`
in `.env`, restart, and the alert count moves. A rule with a number baked into an `if`
is a slide; a rule with a configurable threshold is a system.

Alerts are computed on read, never stored. A stored alert has to be invalidated when
the underlying data changes, and a stale critical alert on a dashboard is worse than no
alert — people learn to ignore the banner.
"""

from __future__ import annotations

from .db import Connection  # driver-neutral: SQLite or Postgres
from datetime import date

from . import db
from .config import settings
from .kpi import ACTIVE_STATUSES, ENROLMENT_WINDOW_DAYS, _today
from .models import Alert, AlertRule, AlertSeverity, utcnow

#: Only studies that are actually recruiting can be behind on recruitment. A study
#: awaiting site activation is at zero enrolment by design, and flagging it buries the
#: studies that are genuinely slipping.
ENROLLING_STATUSES = ("screening", "enrolling", "follow_up")

#: Ordering for display. A breached statutory deadline outranks a slipping recruitment
#: curve, and the dashboard must not make the reader work that out for themselves.
SEVERITY_ORDER = {AlertSeverity.CRITICAL: 0, AlertSeverity.WARNING: 1, AlertSeverity.INFO: 2}


def enrolment_lag(conn: Connection) -> list[Alert]:
    """Studies recruiting below `ENROLMENT_LAG_PCT` of where the plan says they should be.

    Measured against plan-to-date, not against the final target. A study four months into
    a two-year window at 20% of target is on track; the same number at month twenty is not.
    """
    today = _today()
    out: list[Alert] = []
    placeholders = ",".join("?" * len(ENROLLING_STATUSES))

    for s in conn.execute(
        f"SELECT * FROM studies WHERE status IN ({placeholders})", ENROLLING_STATUSES
    ):
        elapsed = (today - date.fromisoformat(s["start_date"])).days
        progress = min(max(elapsed / ENROLMENT_WINDOW_DAYS, 0.0), 1.0)
        expected = int(s["target_enrolment"] * progress)
        if expected <= 0:
            continue  # too early to be behind

        attainment = 100.0 * s["actual_enrolment"] / expected
        if attainment >= settings.enrolment_lag_pct:
            continue

        out.append(
            Alert(
                id=f"ALERT-LAG-{s['id']}",
                rule=AlertRule.ENROLMENT_LAG,
                severity=AlertSeverity.CRITICAL if attainment < 50 else AlertSeverity.WARNING,
                study_id=s["id"],
                study_title=s["title"],
                message=(
                    f"Enrolment at {attainment:.0f}% of plan — {s['actual_enrolment']} subjects "
                    f"against {expected} expected by today "
                    f"(threshold {settings.enrolment_lag_pct:.0f}%)."
                ),
                raised_at=utcnow(),
                deep_link=f"/study/{s['id']}",
            )
        )
    return out


def ethics_renewal_due(conn: Connection) -> list[Alert]:
    """Ethics approvals expiring within `ETHICS_RENEWAL_DAYS`, or already expired.

    An expired approval is not a reminder, it is a stop-work condition: the study has no
    current ethical clearance to be recruiting under.
    """
    today = _today()
    out: list[Alert] = []
    placeholders = ",".join("?" * len(ACTIVE_STATUSES))

    for s in conn.execute(
        f"""SELECT *, {db.days_between('ec_expiry_date', '?')} AS days_left
              FROM studies
             WHERE status IN ({placeholders}) AND ec_expiry_date IS NOT NULL""",
        (today.isoformat(), *ACTIVE_STATUSES),
    ):
        days = s["days_left"]
        if days is None or days > settings.ethics_renewal_days:
            continue

        expired = days < 0
        out.append(
            Alert(
                id=f"ALERT-EC-{s['id']}",
                rule=AlertRule.ETHICS_RENEWAL_DUE,
                severity=AlertSeverity.CRITICAL if expired else AlertSeverity.WARNING,
                study_id=s["id"],
                study_title=s["title"],
                message=(
                    f"Ethics approval expired {abs(days)} days ago ({s['ec_expiry_date']}) — "
                    f"the study has no current clearance."
                    if expired
                    else f"Ethics approval expires in {days} days ({s['ec_expiry_date']}). "
                         f"Renewal submission is due."
                ),
                raised_at=utcnow(),
                deep_link=f"/study/{s['id']}",
            )
        )
    return out


def monitoring_visit_overdue(conn: Connection) -> list[Alert]:
    """Monitoring visits more than `MONITORING_OVERDUE_DAYS` past schedule and not done.

    One alert per study rather than one per visit. Twelve rows saying the same thing
    about the same study is noise, and noise is how a real breach gets scrolled past.
    """
    today = _today()
    cutoff = date.fromordinal(today.toordinal() - settings.monitoring_overdue_days).isoformat()
    out: list[Alert] = []

    for row in conn.execute(
        """SELECT s.id, s.title, COUNT(*) AS n, MIN(v.scheduled_date) AS oldest
             FROM visits v JOIN studies s ON s.id = v.study_id
            WHERE v.monitoring_visit = 1 AND v.actual_date IS NULL AND v.scheduled_date < ?
            GROUP BY s.id, s.title""",
        (cutoff,),
    ):
        days_late = (today - date.fromisoformat(row["oldest"])).days
        out.append(
            Alert(
                id=f"ALERT-MV-{row['id']}",
                rule=AlertRule.MONITORING_VISIT_OVERDUE,
                severity=AlertSeverity.CRITICAL if days_late > 90 else AlertSeverity.WARNING,
                study_id=row["id"],
                study_title=row["title"],
                message=(
                    f"{row['n']} monitoring visit{'' if row['n'] == 1 else 's'} overdue — "
                    f"the oldest was scheduled {days_late} days ago "
                    f"(threshold {settings.monitoring_overdue_days} days)."
                ),
                raised_at=utcnow(),
                deep_link=f"/study/{row['id']}",
            )
        )
    return out


#: The rule set. Adding a rule means adding a function here, nothing else.
RULES = (enrolment_lag, ethics_renewal_due, monitoring_visit_overdue)


def evaluate(conn: Connection) -> list[Alert]:
    """Run every rule and return the alerts, most severe first."""
    raised = [alert for rule in RULES for alert in rule(conn)]
    return sorted(raised, key=lambda a: (SEVERITY_ORDER[a.severity], a.study_id))


if __name__ == "__main__":
    from .db import connect

    alerts = evaluate(connect())
    print(f"{len(alerts)} alert(s) at thresholds "
          f"lag<{settings.enrolment_lag_pct:.0f}%  ec<{settings.ethics_renewal_days}d  "
          f"mv>{settings.monitoring_overdue_days}d")
    for a in alerts:
        print(f"  [{a.severity.value:<8}] {a.study_id}  {a.message}")
