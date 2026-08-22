"""Pharmacovigilance — term coding and statutory reporting clocks.

Two jobs.

**Coding.** A free-text narrative ("patient had a bad headache") is matched to a
controlled term ("Headache", VW-T0001) so events can be counted, compared across
studies, and surfaced as a safety signal. Free text cannot be aggregated; two sites
writing "loose motion" and "diarrhoea" describe one signal and count as none.

The vocabulary is `app/terms.csv` — **our own, written for this demonstration.**
MedDRA and WHODrug are the real dictionaries and they are licensed; we do not have
them, we do not approximate them, and every coded result carries `source="curated"`
so nothing downstream can quietly imply otherwise. The interface is the part that
matters: swap the CSV for a licensed dictionary and `code()` does not change.

**Clocks.** New Drugs and Clinical Trials Rules 2019, Third Schedule: a serious adverse
event must reach the Ethics Committee and the licensing authority **within 24 hours** of
the investigator becoming aware of it, with a full narrative **within 14 days**. Those
deadlines are stored fields computed from the server clock at intake, not a countdown
drawn over a date — the moment the clock started is itself a regulated fact and has to
survive a refresh, an export and an inspection.
"""

from __future__ import annotations

import csv
import difflib
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from .config import settings
from .models import CodingSource, TimelineStatus

TERMS_CSV = Path(__file__).resolve().parent / "terms.csv"

#: Below this, a fuzzy match is a guess rather than a suggestion, and a wrong coded term
#: is worse than an uncoded one — it hides an event inside the wrong bucket.
#:
#: Set at 0.80 rather than higher because morphological variants land there:
#: "syncopal" against "syncope" scores 0.80, and letting a serious event go uncoded to
#: avoid a weak second suggestion is the wrong trade. `MIN_FUZZY_LEN` is what keeps this
#: floor safe; without it, 0.80 would code half the portfolio as flatulence.
FUZZY_FLOOR = 0.80

#: Fuzzy matching is only attempted on synonyms at least this long. Short ones score
#: absurdly well against unrelated words — "gas" against "as" rates 0.80 — so a low
#: minimum turns a routine note into a spurious gastrointestinal event. Short synonyms
#: still match exactly and as phrases; they just do not get to guess.
MIN_FUZZY_LEN = 7

_PUNCT = re.compile(r"[^a-z0-9\s]+")
_SPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace.

    Coding must not care that one site wrote "Head-ache." and another "head ache".
    """
    return _SPACE.sub(" ", _PUNCT.sub(" ", text.lower())).strip()


@dataclass(frozen=True)
class Term:
    code: str
    term: str
    soc: str
    synonyms: tuple[str, ...]


@dataclass(frozen=True)
class CodingResult:
    code: str
    term: str
    soc: str
    confidence: float
    #: How the match was made — shown in the UI so a 0.78 fuzzy hit is never mistaken
    #: for an exact one.
    method: str
    source: CodingSource = CodingSource.CURATED

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "term": self.term,
            "soc": self.soc,
            "confidence": self.confidence,
            "method": self.method,
            "source": self.source.value,
        }


@lru_cache(maxsize=1)
def load_terms(path: str | None = None) -> tuple[Term, ...]:
    """Read the vocabulary once. Synonyms are normalised at load, not per query."""
    with open(path or TERMS_CSV, newline="", encoding="utf-8") as fh:
        return tuple(
            Term(
                code=row["code"],
                term=row["term"],
                soc=row["soc"],
                synonyms=tuple(
                    normalise(s) for s in (row["synonyms"] or row["term"]).split("|") if s.strip()
                ),
            )
            for row in csv.DictReader(fh)
        )


def _phrase_present(phrase: str, text: str) -> bool:
    """Whole-word containment.

    Word boundaries are not optional here: "mi" and "gas" are legitimate synonyms and
    both appear inside dozens of unrelated words. Plain substring matching would code
    "administered" as a myocardial infarction.
    """
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def _best_window_ratio(phrase: str, words: list[str]) -> float:
    """Best `difflib` ratio between a synonym and any same-length run of words.

    Comparing a two-word synonym against a forty-word narrative always scores near zero,
    because most of the narrative is irrelevant to the match. Sliding a window the size
    of the synonym is what lets "diarhea" find "diarrhoea" inside a full sentence.
    """
    n = len(phrase.split())
    best = 0.0
    for size in {max(1, n - 1), n, n + 1}:
        for i in range(0, max(1, len(words) - size + 1)):
            window = " ".join(words[i : i + size])
            ratio = difflib.SequenceMatcher(None, phrase, window).ratio()
            if ratio > best:
                best = ratio
    return best


def code(narrative: str, limit: int = 3) -> list[CodingResult]:
    """Match a narrative to controlled terms, best first.

    Three passes, in descending order of trust:

    1. **exact** — the whole narrative is the synonym. Confidence 1.0.
    2. **phrase** — the synonym appears as whole words inside the narrative. Confidence
       scales with how much of the narrative the phrase accounts for, so "headache" in a
       three-word note is a stronger signal than the same word buried in a paragraph.
    3. **fuzzy** — `difflib` over a sliding window, for typos and spelling variants.

    Returns an empty list rather than a low-confidence guess when nothing clears the
    floor. Uncoded is an honest state; miscoded is not.
    """
    text = normalise(narrative)
    if not text:
        return []
    words = text.split()
    hits: dict[str, CodingResult] = {}

    for entry in load_terms():
        best: tuple[float, str] | None = None

        for syn in entry.synonyms:
            if syn == text:
                best = (1.0, "exact")
                break
            if _phrase_present(syn, text):
                # Coverage: how much of the note this phrase accounts for, floored so a
                # confirmed phrase match never drops into fuzzy territory.
                coverage = len(syn.split()) / max(len(words), 1)
                score = round(min(0.97, 0.85 + 0.12 * coverage), 3)
                if best is None or score > best[0]:
                    best = (score, "phrase")

        if best is None:
            ratio = max(
                (_best_window_ratio(s, words) for s in entry.synonyms if len(s) >= MIN_FUZZY_LEN),
                default=0.0,
            )
            if ratio >= FUZZY_FLOOR:
                best = (round(ratio, 3), "fuzzy")

        if best is not None:
            existing = hits.get(entry.code)
            if existing is None or best[0] > existing.confidence:
                hits[entry.code] = CodingResult(
                    code=entry.code, term=entry.term, soc=entry.soc,
                    confidence=best[0], method=best[1],
                )

    return sorted(hits.values(), key=lambda r: (-r.confidence, r.term))[:limit]


def code_best(narrative: str) -> CodingResult | None:
    """The single best match, or None if nothing cleared the floor."""
    results = code(narrative, limit=1)
    return results[0] if results else None


def code_uncoded_events(conn: sqlite3.Connection, commit: bool = True) -> int:
    """Code every adverse event that has no term yet. Returns how many were coded.

    Used by the seeder, and safe to re-run: an event that already has a term is left
    alone, so a re-run never overwrites a human's coding decision with a machine's.
    """
    rows = conn.execute(
        "SELECT id, narrative FROM adverse_events WHERE coded_term IS NULL"
    ).fetchall()
    n = 0
    for row in rows:
        result = code_best(row["narrative"])
        if result is None:
            continue
        conn.execute(
            """UPDATE adverse_events
                  SET coded_term = ?, coded_code = ?, coding_confidence = ?, coding_source = ?
                WHERE id = ?""",
            (result.term, result.code, result.confidence, result.source.value, row["id"]),
        )
        n += 1
    if commit:
        conn.commit()
    return n


# ------------------------------------------------------------------------- clocks


def compute_clocks(
    reported_at: datetime, serious: bool, now: datetime | None = None
) -> tuple[datetime | None, datetime | None, TimelineStatus]:
    """Return `(deadline_24h, deadline_14d, timeline_status)` for one event.

    A non-serious AE carries no statutory clock at all — `NOT_APPLICABLE` rather than a
    deadline nobody owes. Reporting a non-serious event as if it had a 24-hour deadline
    would be as wrong as missing a real one.

    The status is derived, never stored as an independent truth: recomputing it from the
    deadline is always correct, whereas a stored flag goes stale the moment the clock
    passes while nobody is looking at the page.
    """
    if not serious:
        return None, None, TimelineStatus.NOT_APPLICABLE

    deadline_24h = reported_at + timedelta(hours=settings.sae_initial_report_hours)
    deadline_14d = reported_at + timedelta(days=settings.sae_narrative_days)

    now = now or datetime.now(deadline_24h.tzinfo)
    hours_left = (deadline_24h - now).total_seconds() / 3600

    if hours_left < 0:
        status = TimelineStatus.BREACHED
    elif hours_left < settings.sae_due_soon_hours:
        status = TimelineStatus.DUE_SOON
    else:
        status = TimelineStatus.ON_TRACK

    return deadline_24h, deadline_14d, status


def hours_remaining(deadline: datetime | None, now: datetime | None = None) -> float | None:
    """Signed hours to a deadline. Negative means the deadline has passed — the sign is
    the point, so this deliberately does not clamp at zero."""
    if deadline is None:
        return None
    now = now or datetime.now(deadline.tzinfo)
    return round((deadline - now).total_seconds() / 3600, 1)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print('usage: python -m app.pv "free text narrative"')
        raise SystemExit(2)

    narrative = " ".join(sys.argv[1:])
    results = code(narrative)
    print(f'"{narrative}"')
    print(f"  normalised: {normalise(narrative)}")
    if not results:
        print(f"  no term above the {FUZZY_FLOOR} confidence floor — left uncoded")
        raise SystemExit(1)
    for i, r in enumerate(results):
        marker = "→" if i == 0 else " "
        print(f"  {marker} {r.term:<32} {r.code}  {r.confidence:.2f}  {r.method:<6} source={r.source.value}")
    print(f"  ({len(load_terms())} terms in app/terms.csv — curated for this demo, not MedDRA)")
