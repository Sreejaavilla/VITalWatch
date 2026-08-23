"""Clinical Investigation — assembling evidence about one trial into one view.

A signal says something may be wrong. It does not say what happened. This module is the
layer between the two: it gathers the protocol, the recruitment position, the individual
adverse events, the retrieved literature and the disproportionality result for a single
study, and presents them as connected evidence rather than five screens a person has to
hold in their head at once.

**Two rules govern everything below, and they are the reason this is defensible.**

*Nothing here is a caption.* Every figure on the investigation board is computed from the
database at request time by the same functions the rest of the application uses —
`kpi.study_kpi` for recruitment, `signals.detect` for disproportionality, `pv` for the
coded terms. Change a row and the case changes. A case file with numbers typed into a
template is a slide, not a system, and would not survive the first judge who asked where
a figure came from.

*The system does not make the clinical determination.* It reports a pattern, states what
it consists of, and stops. Nothing in this module concludes that AYU-008 caused hepatic
injury, and nothing concludes the monitoring interval is inadequate — both are questions
for an investigator, and a system that answers them is overstepping in the one domain
where overstepping is least acceptable. What it does instead is make the determination
cheap to reach and impossible to lose: the decision a human takes goes into the audit
chain with its evidence attached.

The clustering is proximity in *exposure time*, not calendar time. The three AYU-008
events are weeks apart by date and nine days apart by day-on-treatment, which is exactly
why they read as unrelated in a chronological event list and as a pattern here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from . import case_data, kpi, retrieval, signals
from .audit import record
from .db import Connection
from .models import utcnow

#: Two events count as part of one pattern when their day-on-treatment values fall
#: inside this many days of each other. A window, not a p-value: it says the events are
#: close in exposure, which is what makes them worth a person's attention.
CLUSTER_WINDOW_DAYS = 14

#: The query the investigation runs against the corpus. Built from the coded term the
#: events actually resolved to, plus the site's own wording — deliberately including
#: "deranged LFT", which appears in no document in the corpus and which therefore only
#: the concept retriever can act on.
def default_query(term: str | None) -> str:
    return f"{term or 'adverse event'} deranged LFT monitoring interval"


@dataclass(frozen=True)
class EventCard:
    subject_code: str
    narrative: str
    coded_term: str | None
    coded_code: str | None
    confidence: float | None
    onset_date: str
    day_on_treatment: int | None
    severity: str
    causality: str
    outcome: str


@dataclass(frozen=True)
class Cluster:
    """A set of events sharing a coded term and close in exposure time."""

    coded_term: str
    coded_code: str
    events: tuple[EventCard, ...]
    first_day: int
    last_day: int

    @property
    def size(self) -> int:
        return len(self.events)

    @property
    def span_days(self) -> int:
        return self.last_day - self.first_day

    @property
    def calendar_span_days(self) -> int:
        dates = sorted(date.fromisoformat(e.onset_date) for e in self.events)
        return (dates[-1] - dates[0]).days


def _day_on_treatment(conn: Connection, subject_code: str, onset: str) -> int | None:
    row = conn.execute(
        "SELECT enrolled_date FROM subjects WHERE subject_code = ?", (subject_code,)
    ).fetchone()
    if row is None or not row["enrolled_date"]:
        return None
    return (date.fromisoformat(onset) - date.fromisoformat(row["enrolled_date"])).days


def events(conn: Connection, study_id: str) -> list[EventCard]:
    """Every adverse event on the study, with exposure day worked out for each."""
    rows = conn.execute(
        """SELECT subject_code, narrative, coded_term, coded_code, coding_confidence,
                  onset_date, severity, causality, outcome
             FROM adverse_events WHERE study_id = ? ORDER BY onset_date""",
        (study_id,),
    ).fetchall()
    return [
        EventCard(
            subject_code=r["subject_code"],
            narrative=r["narrative"],
            coded_term=r["coded_term"],
            coded_code=r["coded_code"],
            confidence=r["coding_confidence"],
            onset_date=r["onset_date"],
            day_on_treatment=_day_on_treatment(conn, r["subject_code"], r["onset_date"]),
            severity=r["severity"],
            causality=r["causality"],
            outcome=r["outcome"],
        )
        for r in rows
    ]


def cluster(cards: list[EventCard]) -> Cluster | None:
    """The largest group of events sharing a term and falling inside the window.

    Returns None when no group reaches the case floor the safety screen already uses, so
    the investigation cannot claim a pattern the signals page would not flag.
    """
    by_term: dict[tuple[str, str], list[EventCard]] = {}
    for card in cards:
        if card.coded_term and card.day_on_treatment is not None:
            by_term.setdefault((card.coded_term, card.coded_code or ""), []).append(card)

    best: Cluster | None = None
    for (term, code), group in by_term.items():
        group = sorted(group, key=lambda c: c.day_on_treatment or 0)
        days = [c.day_on_treatment or 0 for c in group]
        if len(group) < signals.MIN_CASES or days[-1] - days[0] > CLUSTER_WINDOW_DAYS:
            continue
        candidate = Cluster(term, code, tuple(group), days[0], days[-1])
        if best is None or candidate.size > best.size:
            best = candidate
    return best


def recruitment(conn: Connection, study_id: str) -> dict:
    """Enrolment against plan, from the same KPI function the study page uses."""
    k = kpi.study_kpi(conn, study_id)
    expected = k.expected_by_today
    deviation = 0.0 if not expected else round(100.0 * (k.enrolled - expected) / expected, 1)

    # Site-level spread, which is what makes "site variation" a fact rather than a guess.
    by_site = conn.execute(
        """SELECT si.name, si.city, COUNT(su.id) AS enrolled
             FROM sites si
             JOIN study_sites ss ON ss.site_id = si.id AND ss.study_id = ?
             LEFT JOIN subjects su ON su.site_id = si.id AND su.study_id = ?
                                  AND su.status != 'screen_failed'
            GROUP BY si.id, si.name, si.city
            ORDER BY enrolled DESC, si.name""",
        (study_id, study_id),
    ).fetchall()
    total = sum(r["enrolled"] for r in by_site) or 1
    top4 = sum(r["enrolled"] for r in by_site[:4])

    return {
        "kpi": k,
        "expected": expected,
        "deviation_pct": deviation,
        "by_site": by_site,
        "top4_share": round(100.0 * top4 / total),
        "risk": "HIGH" if deviation <= -25 else "MEDIUM" if deviation <= -10 else "LOW",
        "factors": case_data.RECRUITMENT_FACTORS,
    }


def disproportionality(conn: Connection, study_id: str) -> signals.Signal | None:
    """This study's flagged signal, if the screen raised one. Not recomputed here —
    the same `signals.detect` the safety page runs, so the two cannot disagree."""
    found = [s for s in signals.detect(conn) if s.study_id == study_id and s.flagged]
    return found[0] if found else None


def indicators(conn: Connection, study_id: str) -> list[dict]:
    """The four case-file lights. Each derives from data, and each says why it is lit."""
    rec = recruitment(conn, study_id)
    cards = events(conn, study_id)
    found = cluster(cards)
    signal = disproportionality(conn, study_id)

    detail = {
        "recruitment": (
            "amber" if rec["deviation_pct"] < 0 else "green",
            f"{rec['deviation_pct']:+.1f}% against plan-to-date"
            f" ({rec['kpi'].enrolled} of {rec['expected']} expected)",
        ),
        "events": (
            "red" if found else "green",
            f"{found.size} similar events within {found.span_days} days of exposure"
            if found else "no cluster above the case floor",
        ),
        "signal": (
            "red" if signal else "green",
            f"{signal.coded_term} — PRR {signal.prr:.2f}"
            if signal and signal.prr is not None
            else f"{signal.coded_term} — not seen elsewhere" if signal
            else "nothing above the screening criterion",
        ),
        "protocol": (
            "amber" if found else "green",
            "monitoring schedule relevant to the observed timing"
            if found else "no observation",
        ),
    }
    return [
        {"label": label, "key": key, "definition": definition,
         "tone": detail[key][0], "value": detail[key][1]}
        for label, key, definition in case_data.INDICATORS
    ]


def evidence_graph(conn: Connection, study_id: str, fused: list) -> dict:
    """The node/edge structure the board draws.

    Assembled here rather than in the template so that what the picture shows and what
    the page says come from one place.
    """
    cards = events(conn, study_id)
    found = cluster(cards)
    signal = disproportionality(conn, study_id)
    return {
        "study": study_id,
        "protocol": case_data.PROTOCOL["Monitoring"],
        "cluster": found,
        "signal": signal,
        "sources": [
            {"id": h.document.id, "kind": h.document.kind, "title": h.document.title,
             "found_by": h.found_by}
            for h in fused
        ],
    }


def report(conn: Connection, study_id: str) -> dict:
    """The investigation finding: what was observed, from what, and what is still open.

    Deliberately has no `conclusion` field. The confidence line is an instruction to a
    human, not a probability, because a number here would imply the system had weighed
    causation — which it has not and cannot.
    """
    rec = recruitment(conn, study_id)
    cards = events(conn, study_id)
    found = cluster(cards)
    signal = disproportionality(conn, study_id)
    query = default_query(found.coded_term if found else None)
    hits = retrieval.search(query)

    observations = []
    if found:
        observations.append(
            f"{found.size} events coded to {found.coded_term} ({found.coded_code}) "
            f"between day {found.first_day} and day {found.last_day} of exposure — "
            f"{found.span_days} days apart on treatment, {found.calendar_span_days} days "
            f"apart by calendar date."
        )
    if signal and signal.prr is not None:
        observations.append(
            f"Disproportionality screen returns PRR {signal.prr:.2f} for "
            f"{signal.coded_term} in this study against the rest of the portfolio."
        )
    if found:
        observations.append(case_data.PROTOCOL_OBSERVATION)
    observations.append(
        f"{rec['deviation_pct']:+.1f}% recruitment against plan-to-date "
        f"({rec['kpi'].enrolled} enrolled, {rec['expected']} expected by today)."
    )
    observations.append(
        f"{len(hits['fused'])} supporting documents retrieved from a corpus of "
        f"{hits['corpus_size']}, ranked by reciprocal rank fusion over two retrievers."
    )

    return {
        "case_id": case_data.CASE_ID,
        "study_id": study_id,
        "finding": (
            f"Potential emerging safety pattern — {found.coded_term} ({found.coded_code})"
            if found else "No safety pattern above the screening criterion."
        ),
        "observations": observations,
        "confidence": "Requires investigator assessment",
        "next_step": (
            "Review the safety pattern, the protocol monitoring requirements and the "
            "supporting evidence before determining further action."
        ),
        "cluster": found,
        "signal": signal,
        "recruitment": rec,
        "retrieval": hits,
        "query": query,
    }


# ------------------------------------------------------------------------- decisions


def decisions(conn: Connection, case_id: str) -> list:
    return conn.execute(
        """SELECT * FROM investigation_decisions WHERE case_id = ?
            ORDER BY decided_at DESC""",
        (case_id,),
    ).fetchall()


def decide(
    conn: Connection,
    *,
    case_id: str,
    study_id: str,
    action: str,
    reason: str,
    actor: str,
    evidence_count: int,
) -> dict:
    """Record an investigator's decision, and its audit row, in one transaction.

    The same rule as every other mutation in this system: the audit write is not a
    follow-up, it is part of the same commit. A decision that could be recorded without
    its trail would be worth less than no decision at all, because it would look
    accountable without being so.
    """
    if action not in case_data.DECISIONS:
        raise ValueError(f"unknown decision {action!r}")

    row = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "study_id": study_id,
        "action": action,
        "reason": reason,
        "actor": actor,
        "evidence_count": evidence_count,
        "decided_at": utcnow().isoformat(),
    }
    conn.execute(
        """INSERT INTO investigation_decisions
           (id, case_id, study_id, action, reason, actor, evidence_count, decided_at)
           VALUES (:id,:case_id,:study_id,:action,:reason,:actor,:evidence_count,:decided_at)""",
        row,
    )
    event = record(
        conn,
        actor=actor,
        action="create",
        resource_type="investigation_decision",
        resource_id=case_id,
        after={
            "case_id": case_id,
            "study_id": study_id,
            "action": action,
            "evidence_count": evidence_count,
        },
        reason=reason,
        commit=False,
    )
    conn.commit()
    return {"decision": row, "audit": event}
