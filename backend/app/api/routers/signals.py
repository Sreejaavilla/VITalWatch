"""/api/signals — DSMB safety signal view. OWNER: Sreeja.

PHASE 0 PLACEHOLDER: counts by coded term from the seeded AEs.
Phase 2: aggregate by term x study x severity. Phase 4: disproportionality.
"""

from collections import Counter

from fastapi import APIRouter
from pydantic import BaseModel

from ...stubs import loader

router = APIRouter(prefix="/api/signals", tags=["pharmacovigilance"])


class TermSignal(BaseModel):
    term: str
    count: int
    serious_count: int
    studies: list[str]


@router.get("", response_model=list[TermSignal], summary="AE counts aggregated by coded term")
def aggregate_signals(study_id: str | None = None) -> list[TermSignal]:
    aes = loader.load("adverse_events")
    if study_id:
        aes = [a for a in aes if a["study_id"] == study_id]

    counts: Counter = Counter(a.get("coded_term") or "Uncoded" for a in aes)
    return [
        TermSignal(
            term=term,
            count=n,
            serious_count=sum(1 for a in aes if (a.get("coded_term") or "Uncoded") == term and a.get("serious")),
            studies=sorted({a["study_id"] for a in aes if (a.get("coded_term") or "Uncoded") == term}),
        )
        for term, n in counts.most_common()
    ]
