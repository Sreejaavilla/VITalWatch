"""Role lenses over the same data.

Three people open this system with three different questions, and a single dashboard
answers none of them well. An investigator wants to know whether *their* trial is
slipping. A safety officer wants to know whether anything needs investigating before
the end of the day. Institutional leadership wants to know whether the portfolio is
compliant and audit-ready. Those are different questions, so they get different
selections of the same numbers.

**A lens is not access control.** Nothing here restricts anything: every screen stays
reachable from every lens, and switching lens changes what is shown first, not what is
permitted. Authentication is deliberately not built (see the home page), and a role
switcher that looked like authorisation while enforcing nothing would be the dishonest
version of this feature. The distinction is stated on the page itself.

Every metric carries the definition of what it counts, for the same reason `kpi.py`
does: "open queries" and "overdue visits" are exactly the figures two people define
differently and then disagree about on stage.
"""

from __future__ import annotations

from .db import Connection  # driver-neutral: SQLite or Postgres
from dataclasses import dataclass
from datetime import date, timedelta

from . import alerts, audit, db, kpi, signals
from .config import settings
from .kpi import ACTIVE_STATUSES, ENROLMENT_WINDOW_DAYS, OPEN_SAE_OUTCOMES, _today


@dataclass(frozen=True)
class Metric:
    """One headline figure on a role dashboard.

    `definition` is not decoration — it is what makes the number defensible when
    somebody asks what it actually counts.
    """

    label: str
    value: str
    sub: str | None = None
    tone: str = "neutral"          # neutral | good | warn | bad
    href: str | None = None
    definition: str = ""


@dataclass(frozen=True)
class Role:
    id: str
    name: str
    question: str
    #: What this lens puts first, in one line.
    focus: str


ROLES: tuple[Role, ...] = (
    Role(
        id="investigator",
        name="Investigator",
        question="How is my trial progressing?",
        focus="Enrolment against plan, visit compliance, open queries and safety events "
              "for the studies this investigator is running.",
    ),
    Role(
        id="safety",
        name="Pharmacovigilance officer",
        question="Is there a safety risk I need to investigate?",
        focus="Serious events ordered by statutory clock, coding coverage, and coded "
              "terms ranked by proportional reporting ratio.",
    ),
    Role(
        id="leadership",
        name="Institutional leadership",
        question="Is the institution compliant, on schedule and audit-ready?",
        focus="Portfolio-wide performance, regulatory milestones, oversight coverage "
              "and the integrity of the audit trail.",
    ),
)

BY_ID = {r.id: r for r in ROLES}


def _scalar(conn: Connection, sql: str, params: tuple = ()) -> int:
    return conn.execute(sql, params).fetchone()[0] or 0


def _expected(start_date: str, target: int, today: date) -> int:
    """Where the enrolment plan says a study should be today. Same straight line as
    `kpi.study_kpi`, so the two screens cannot disagree."""
    elapsed = (today - date.fromisoformat(start_date)).days
    return int(target * min(max(elapsed / ENROLMENT_WINDOW_DAYS, 0.0), 1.0))


def _pct(part: int, whole: int) -> float:
    return 0.0 if not whole else round(100.0 * part / whole, 1)


# ------------------------------------------------------------------- investigator


def investigators(conn: Connection) -> list[str]:
    """Every PI with at least one study, most studies first — the scope selector."""
    return [
        r[0]
        for r in conn.execute(
            "SELECT pi_name, COUNT(*) n FROM studies GROUP BY pi_name ORDER BY n DESC, pi_name"
        )
    ]


def investigator(conn: Connection, pi: str) -> dict:
    """The investigator lens, scoped to one principal investigator.

    Scoping to a real `pi_name` rather than showing the whole portfolio is the point:
    an investigator dashboard that lists other people's trials is the portfolio page
    with a different heading.
    """
    today = _today()
    rows = conn.execute(
        """SELECT s.*,
                  (SELECT COUNT(*) FROM queries q
                    WHERE q.study_id = s.id AND q.status != 'closed')  AS open_queries,
                  (SELECT COUNT(*) FROM adverse_events a
                    WHERE a.study_id = s.id AND a.serious = 1
                      AND a.outcome IN ('recovering','not_recovered','unknown')) AS open_saes
             FROM studies s WHERE s.pi_name = ? ORDER BY s.id""",
        (pi,),
    ).fetchall()

    ids = [r["id"] for r in rows]
    marks = ",".join("?" * len(ids)) or "NULL"
    active = [r for r in rows if r["status"] in ACTIVE_STATUSES]

    enrolled = sum(r["actual_enrolment"] for r in active)
    target = sum(r["target_enrolment"] for r in active)
    expected = sum(_expected(r["start_date"], r["target_enrolment"], today) for r in active)

    due = _scalar(
        conn,
        f"""SELECT COUNT(*) FROM visits WHERE study_id IN ({marks})
             AND monitoring_visit = 0 AND scheduled_date <= ?""",
        (*ids, today.isoformat()),
    )
    done = _scalar(
        conn,
        f"""SELECT COUNT(*) FROM visits WHERE study_id IN ({marks})
             AND monitoring_visit = 0 AND scheduled_date <= ? AND status = 'completed'""",
        (*ids, today.isoformat()),
    )
    compliance = _pct(done, due)

    queries = sum(r["open_queries"] for r in rows)
    ageing = conn.execute(
        f"""SELECT AVG({db.days_between('?', 'raised_date')}) FROM queries
             WHERE study_id IN ({marks}) AND status != 'closed'""",
        (today.isoformat(), *ids),
    ).fetchone()[0]
    ageing = float(ageing) if ageing is not None else None
    saes = sum(r["open_saes"] for r in rows)

    nxt = conn.execute(
        f"""SELECT m.type, m.planned_date, m.study_id FROM milestones m
             WHERE m.study_id IN ({marks}) AND m.actual_date IS NULL AND m.planned_date >= ?
             ORDER BY m.planned_date ASC LIMIT 1""",
        (*ids, today.isoformat()),
    ).fetchone()

    attainment = _pct(enrolled, expected)
    metrics = [
        Metric("My studies", str(len(active)), f"{len(rows)} total incl. closed",
               href="/portfolio",
               definition="Studies where this PI is named, counted as active from ethics "
                          "approval until close-out."),
        Metric("Enrolment vs plan", f"{attainment:.0f}%",
               f"{enrolled} enrolled · plan to date {expected} · target {target}",
               tone="bad" if attainment < 50 else "warn" if attainment < settings.enrolment_lag_pct else "good",
               href="/portfolio",
               definition="Actual enrolment as a percentage of where the straight-line plan "
                          "says these studies should be today — not of the final target, so "
                          "a study that has only just opened is not penalised for being young."),
        Metric("Visit compliance", f"{compliance:.0f}%", f"{done} of {due} due by today",
               tone="good" if compliance >= 90 else "warn" if compliance >= 75 else "bad",
               definition="Subject visits completed, out of those scheduled on or before "
                          "today. Future visits are excluded — they are neither compliant "
                          "nor non-compliant yet."),
        Metric("Open queries", str(queries),
               f"average {round(ageing or 0.0, 1)} days old" if queries else "none outstanding",
               tone="warn" if queries else "good",
               definition="Data queries not yet closed. An answered-but-unclosed query is "
                          "still open — somebody still has to accept the answer."),
        Metric("Open SAEs", str(saes),
               "outcome not yet final" if saes else "none open",
               tone="bad" if saes else "good", href="/ae",
               definition="Serious adverse events on these studies whose outcome is still "
                          "recovering, not recovered, or unknown."),
        Metric("Next milestone",
               f"{(date.fromisoformat(nxt['planned_date']) - today).days}d" if nxt else "—",
               (f"{nxt['type'].replace('_', ' ')} · {nxt['study_id']}" if nxt
                else "nothing scheduled ahead"),
               href=f"/study/{nxt['study_id']}" if nxt else None,
               definition="The soonest planned milestone across these studies that has not "
                          "yet been recorded as done."),
    ]

    # Their studies, each with the gap between actual and plan made visible.
    queue = [
        {"study": r, "expected": _expected(r["start_date"], r["target_enrolment"], today)}
        for r in rows
    ]
    mine = set(ids)

    return {
        "metrics": metrics,
        "scope": pi,
        "studies": queue,
        "alerts": [a for a in alerts.evaluate(conn) if a.study_id in mine],
    }


# -------------------------------------------------------------------------- safety


def safety(conn: Connection) -> dict:
    """The pharmacovigilance lens: statutory clocks first, then disproportionality."""
    today = _today()
    total_ae = _scalar(conn, "SELECT COUNT(*) FROM adverse_events")
    coded = _scalar(conn, "SELECT COUNT(*) FROM adverse_events WHERE coded_term IS NOT NULL")
    breached = _scalar(conn, "SELECT COUNT(*) FROM adverse_events WHERE timeline_status = 'breached'")
    due_soon = _scalar(conn, "SELECT COUNT(*) FROM adverse_events WHERE timeline_status = 'due_soon'")

    marks = ",".join("?" * len(OPEN_SAE_OUTCOMES))
    open_saes = _scalar(
        conn,
        f"SELECT COUNT(*) FROM adverse_events WHERE serious = 1 AND outcome IN ({marks})",
        OPEN_SAE_OUTCOMES,
    )
    narratives = _scalar(
        conn,
        "SELECT COUNT(*) FROM adverse_events WHERE serious = 1 AND deadline_14d IS NOT NULL "
        "AND deadline_14d >= ? AND deadline_14d <= ?",
        (today.isoformat(), (today + timedelta(days=14)).isoformat()),
    )

    found = signals.detect(conn)
    flagged = [s for s in found if s.flagged]
    # `detect` already ranks flagged first and puts terms with an undefined ratio — seen
    # in one study and nowhere else — above measured ones. Re-sorting here by PRR alone
    # would drop exactly those to the bottom and then report "nothing above threshold"
    # next to a non-zero count.
    top = flagged[0] if flagged else None

    # The worklist: every serious event with a live clock, soonest deadline first.
    worklist = conn.execute(
        """SELECT a.*, s.title AS study_title FROM adverse_events a
             JOIN studies s ON s.id = a.study_id
            WHERE a.serious = 1
            ORDER BY CASE a.timeline_status
                       WHEN 'breached' THEN 0 WHEN 'due_soon' THEN 1 ELSE 2 END,
                     a.deadline_24h ASC""",
    ).fetchall()

    coverage = _pct(coded, total_ae)
    metrics = [
        Metric("Open SAEs", str(open_saes), "outcome not yet final",
               tone="bad" if open_saes else "good", href="/ae",
               definition="Serious adverse events whose outcome is still recovering, not "
                          "recovered, or unknown."),
        Metric("24-hour deadline breached", str(breached),
               "reportable to EC and licensing authority",
               tone="bad" if breached else "good", href="/ae",
               definition="Serious events whose 24-hour reporting deadline under the New "
                          "Drugs and Clinical Trials Rules 2019 has already passed."),
        Metric("Due within " + str(settings.sae_due_soon_hours) + "h", str(due_soon),
               "clock still running",
               tone="warn" if due_soon else "good", href="/ae",
               definition="Serious events whose 24-hour deadline falls inside the warning "
                          f"window, currently {settings.sae_due_soon_hours} hours "
                          "(SAE_DUE_SOON_HOURS)."),
        Metric("14-day narratives due", str(narratives), "within the next fortnight",
               tone="warn" if narratives else "good",
               definition="Serious events whose 14-day narrative deadline falls between "
                          "today and fourteen days from today."),
        Metric("Coding coverage", f"{coverage:.0f}%", f"{coded} of {total_ae} events coded",
               tone="good" if coverage >= 95 else "warn",
               definition="Events matched to a term in the curated vocabulary above the "
                          "confidence floor. An unmatched narrative stays uncoded rather "
                          "than being guessed into the wrong bucket."),
        Metric("Signals above threshold", str(len(flagged)),
               (("highest PRR %.1f — %s" % (top.prr, top.coded_term)) if top and top.prr is not None
                else f"{top.coded_term} — {top.cases} cases, not seen elsewhere" if top
                else "nothing above the screening criterion"),
               tone="bad" if flagged else "good", href="/signals",
               definition=f"Coded terms with at least {signals.MIN_CASES} cases in a study "
                          f"and PRR ≥ {signals.PRR_THRESHOLD:g}. A triage order, not an "
                          "incidence rate and not causation."),
    ]

    return {
        "metrics": metrics,
        "worklist": worklist,
        # Truncated for the summary view, and the page says so rather than presenting a
        # cut-down list as if it were the whole analysis. /signals shows every row.
        "signals": found[:8],
        "signals_total": len(found),
        "flagged": len(flagged),
    }


# ---------------------------------------------------------------------- leadership


def leadership(conn: Connection) -> dict:
    """The institutional lens: portfolio performance and audit-readiness."""
    today = _today()
    k = kpi.portfolio_kpi(conn)
    raised = alerts.evaluate(conn)
    critical = [a for a in raised if a.severity.value == "critical"]
    chain = audit.verify(conn)

    ec_due = _scalar(
        conn,
        "SELECT COUNT(*) FROM studies WHERE ec_expiry_date IS NOT NULL "
        "AND ec_expiry_date BETWEEN ? AND ?",
        (today.isoformat(), (today + timedelta(days=settings.ethics_renewal_days)).isoformat()),
    )
    marks = ",".join("?" * len(ACTIVE_STATUSES))
    unregistered = _scalar(
        conn,
        f"SELECT COUNT(*) FROM studies WHERE ctri_number IS NULL AND status IN ({marks})",
        ACTIVE_STATUSES,
    )

    attainment = _pct(k.enrolled_total, k.target_total)
    site_pct = _pct(k.sites_activated, k.sites_total)
    metrics = [
        Metric("Active studies", str(k.active_studies),
               f"{k.enrolled_total} of {k.target_total} participants enrolled",
               href="/portfolio",
               definition="Studies between ethics approval and close-out. Protocol-stage "
                          "and closed studies are real portfolio entries but nobody is "
                          "enrolling into them."),
        Metric("Portfolio enrolment", f"{attainment:.0f}%", "of combined target",
               tone="good" if attainment >= 60 else "warn",
               href="/portfolio",
               definition="Enrolment across all active studies as a percentage of their "
                          "combined target. Per-study pacing is on the portfolio page."),
        Metric("Sites activated", f"{k.sites_activated}/{k.sites_total}",
               f"{site_pct:.0f}% of the network",
               tone="good" if site_pct >= 70 else "warn",
               definition="Sites with an activation date recorded, out of every site in "
                          "the institutional network."),
        Metric("Critical alerts", str(len(critical)), f"{len(raised)} alerts in total",
               tone="bad" if critical else "good", href="/portfolio",
               definition="Rule-engine output at critical severity: breached statutory "
                          "deadlines and enrolment below half of plan. Thresholds are read "
                          "from the environment, not compiled in."),
        Metric("Ethics renewals due", str(ec_due),
               f"within {settings.ethics_renewal_days} days"
               + (f" · {unregistered} active without CTRI" if unregistered else ""),
               tone="warn" if ec_due or unregistered else "good",
               definition="Studies whose ethics-committee approval expires inside the "
                          f"renewal window, currently {settings.ethics_renewal_days} days "
                          "(ETHICS_RENEWAL_DAYS)."),
        Metric("Audit chain", "Intact" if chain["ok"] else f"Broken at {chain['seq']}",
               f"{chain['count']} events verified from genesis",
               tone="good" if chain["ok"] else "bad", href="/audit?verify=1",
               definition="Every audit row rehashed and compared against the hash its "
                          "successor committed to. Verification walks the whole chain, "
                          "not a sample."),
    ]

    # Oversight posture: the figures an inspector asks for, with no interpretation.
    posture = [
        ("Overdue monitoring visits", k.overdue_monitoring_visits, "/portfolio",
         f"Scheduled more than {settings.monitoring_overdue_days} days ago and not "
         "conducted, or conducted with no report filed."),
        ("Open data queries", k.open_queries, "/portfolio",
         "Raised and not yet closed, across every study."),
        ("Open SAEs", k.open_saes, "/ae",
         "Serious events whose outcome is not yet final."),
        ("Audit events", chain["count"], "/audit",
         "Append-only. UPDATE and DELETE are refused by the database itself."),
        ("SDTM DM export", "Ready", "/api/export/sdtm/dm.csv",
         "CDISC Study Data Tabulation Model, Demographics domain, streamed as CSV."),
        ("FHIR R4 ResearchStudy", "Ready", "/api/fhir/ResearchStudy/STU-001",
         "HL7 FHIR R4 resource shape, tagged HTEST to mark the data as synthetic."),
    ]

    return {
        "metrics": metrics,
        "alerts": raised,
        "posture": posture,
        "chain": chain,
    }
