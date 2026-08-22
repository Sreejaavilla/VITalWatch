"""/api/ae — adverse event intake. OWNER: Sreeja.

Thin wrapper by design: behaviour lives in services/pv/ so Sreeja can run and test it
with the backend completely down.

PHASE 0 PLACEHOLDER wired by Kavin. Sreeja replaces the bodies with calls into
services.pv.coding and services.pv.timelines.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from contracts.models import AdverseEvent
from ...stubs import loader

router = APIRouter(prefix="/api", tags=["pharmacovigilance"])


class CodingCandidate(BaseModel):
    term: str
    code: str
    score: float
    #: "mock" | "semantic" | "meddra" — never implies a licensed dictionary we don't have.
    source: str


class CodingSuggestion(BaseModel):
    candidates: list[CodingCandidate]


@router.get("/ae", response_model=list[AdverseEvent], summary="List adverse events")
def list_aes(study_id: str | None = None, serious: bool | None = None) -> list[AdverseEvent]:
    records = loader.load("adverse_events")
    if study_id:
        records = [a for a in records if a["study_id"] == study_id]
    if serious is not None:
        records = [a for a in records if a.get("serious") is serious]
    return [AdverseEvent(**a) for a in records]


@router.get("/ae/{ae_id}", response_model=AdverseEvent, summary="One adverse event")
def get_ae(ae_id: str) -> AdverseEvent:
    record = loader.find("adverse_events", "id", ae_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No adverse event {ae_id}")
    return AdverseEvent(**record)


@router.post("/ae", response_model=AdverseEvent, status_code=201, summary="Report an AE/SAE")
def report_ae(payload: AdverseEvent) -> AdverseEvent:
    """PLACEHOLDER: echoes the payload back.

    Sreeja: code the narrative via services.pv.coding, compute the NDCT-2019 deadlines
    via services.pv.timelines from the SERVER clock, then let Caleb's middleware write
    the audit event.
    """
    return payload


@router.post("/coding/suggest", response_model=CodingSuggestion, summary="Suggest coded terms")
def suggest_coding(narrative: str) -> CodingSuggestion:
    """PLACEHOLDER: one fixed candidate. Sreeja: top-3 from the curated subset."""
    return CodingSuggestion(
        candidates=[CodingCandidate(term="Headache", code="MOCK-10019211", score=0.0, source="mock")]
    )
