"""The portfolio as tracks through time.

A table of studies tells you what is true now. It cannot tell you that four trials all
hit their ethics expiry in the same quarter, that one has been recruiting for two years
without a CTRI number, or that a study is a third of the way through its window with a
tenth of its participants. Those are the questions institutional oversight actually
asks, and every one of them is a question about *when*.

So the portfolio is drawn as one track per study on a shared time axis, with today drawn
once as a single line across all of them. That line is the same reserved reference colour
the enrolment marks use, and it means the same thing here: this is the line you are
measured against. A study whose enrolment fill stops well short of the today line is
behind, and you can see it without reading a number.

Geometry is computed here rather than in the template because it is arithmetic with edge
cases — missing dates, studies that start before the window, milestones that fall outside
it — and arithmetic in a Jinja expression is arithmetic nobody can test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from . import kpi
from .db import Connection

#: Milestones worth drawing. The full set is eight, which is more marks than a reader can
#: tell apart at this scale; these four are the ones with a regulatory or recruitment
#: consequence. The rest remain on the study page.
DRAWN_MILESTONES = {
    "ec_approval": ("EC", "approval"),
    "ctri_registration": ("CT", "CTRI registration"),
    "first_subject_in": ("FS", "first subject in"),
    "last_subject_in": ("LS", "last subject in"),
}

#: Breathing room at each end so a marker on the first or last day is not clipped.
PAD_DAYS = 45


@dataclass(frozen=True)
class Mark:
    """A dated event on a track."""

    key: str
    short: str
    label: str
    at: str          # ISO date
    pct: float       # position across the domain
    done: bool


@dataclass
class Track:
    study_id: str
    title: str
    status: str
    phase: str
    pi_name: str
    ctri_number: str | None

    #: Where the study's own window sits within the portfolio domain.
    left_pct: float
    width_pct: float

    #: Enrolment, as a proportion of the *study's own bar*, not of the domain.
    enrolled: int
    target: int
    expected: int
    fill_pct: float
    plan_pct: float

    ec_expiry: str | None
    ec_expiry_pct: float | None
    ec_days_left: int | None

    marks: list[Mark] = field(default_factory=list)

    @property
    def behind(self) -> bool:
        """Below the same threshold the enrolment-lag alert uses, so the picture and the
        alert list cannot disagree about which studies are slipping."""
        from .config import settings

        if self.expected <= 0:
            return False
        return 100.0 * self.enrolled / self.expected < settings.enrolment_lag_pct

    @property
    def attainment(self) -> float:
        return 0.0 if self.expected <= 0 else round(100.0 * self.enrolled / self.expected)


@dataclass
class Portfolio:
    start: date
    end: date
    today: date
    today_pct: float
    tracks: list[Track]
    year_ticks: list[tuple[str, float]]
    quarter_ticks: list[float]


def _pct(day: date, start: date, span: int) -> float:
    return round(100.0 * (day - start).days / span, 3)


def _d(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def build(conn: Connection) -> Portfolio:
    """One track per study across a shared axis."""
    today = kpi._today()
    studies = conn.execute(
        """SELECT s.*,
                  (SELECT COUNT(*) FROM subjects su
                    WHERE su.study_id = s.id AND su.status != 'screen_failed') AS enrolled_now
             FROM studies s ORDER BY s.start_date""",
    ).fetchall()
    if not studies:
        return Portfolio(today, today, today, 0.0, [], [], [])

    milestones: dict[str, list] = {}
    for row in conn.execute(
        "SELECT study_id, type, planned_date, actual_date FROM milestones ORDER BY planned_date"
    ):
        milestones.setdefault(row["study_id"], []).append(row)

    # The domain has to hold every date any track will draw, or a marker lands off the
    # end of its own row.
    dates: list[date] = [today]
    for s in studies:
        dates += [d for d in (_d(s["start_date"]), _d(s["ec_approval_date"]),
                              _d(s["ec_expiry_date"]), _d(s["end_date"])) if d]
        for m in milestones.get(s["id"], []):
            dates += [d for d in (_d(m["planned_date"]), _d(m["actual_date"])) if d]

    start = min(dates) - timedelta(days=PAD_DAYS)
    end = max(dates) + timedelta(days=PAD_DAYS)
    span = max((end - start).days, 1)

    tracks: list[Track] = []
    for s in studies:
        s_start = _d(s["start_date"]) or today
        # A study's bar runs from its start to whichever comes last: its planned end, its
        # ethics expiry, or today. A bar that stopped at today would make every ongoing
        # study look finished.
        s_end = max(d for d in (_d(s["end_date"]), _d(s["ec_expiry_date"]), today) if d)

        left = _pct(s_start, start, span)
        width = max(_pct(s_end, start, span) - left, 0.5)

        expected = kpi.expected_enrolment(s["start_date"], s["target_enrolment"], today)
        target = s["target_enrolment"] or 1

        marks: list[Mark] = []
        for m in milestones.get(s["id"], []):
            if m["type"] not in DRAWN_MILESTONES:
                continue
            when = _d(m["actual_date"]) or _d(m["planned_date"])
            if when is None:
                continue
            short, label = DRAWN_MILESTONES[m["type"]]
            marks.append(Mark(
                key=m["type"], short=short, label=label, at=when.isoformat(),
                pct=_pct(when, start, span), done=bool(m["actual_date"]),
            ))

        expiry = _d(s["ec_expiry_date"])
        tracks.append(Track(
            study_id=s["id"], title=s["title"], status=s["status"], phase=s["phase"],
            pi_name=s["pi_name"], ctri_number=s["ctri_number"],
            left_pct=left, width_pct=width,
            enrolled=s["actual_enrolment"], target=s["target_enrolment"], expected=expected,
            # Enrolment is drawn inside the study's own bar, so the fill is a proportion
            # of that bar rather than of the whole axis.
            fill_pct=round(min(100.0 * s["actual_enrolment"] / target, 100.0), 2),
            plan_pct=round(min(100.0 * expected / target, 100.0), 2),
            ec_expiry=s["ec_expiry_date"],
            ec_expiry_pct=_pct(expiry, start, span) if expiry else None,
            ec_days_left=(expiry - today).days if expiry else None,
            marks=marks,
        ))

    year_ticks = []
    for year in range(start.year, end.year + 1):
        first = date(year, 1, 1)
        if start <= first <= end:
            year_ticks.append((str(year), _pct(first, start, span)))

    quarter_ticks = []
    for year in range(start.year, end.year + 1):
        for month in (4, 7, 10):
            q = date(year, month, 1)
            if start <= q <= end:
                quarter_ticks.append(_pct(q, start, span))

    return Portfolio(
        start=start, end=end, today=today, today_pct=_pct(today, start, span),
        tracks=tracks, year_ticks=year_ticks, quarter_ticks=quarter_ticks,
    )
