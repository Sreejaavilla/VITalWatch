"""/api/enrolment. OWNER: Kavin."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...stubs import loader

router = APIRouter(prefix="/api/enrolment", tags=["enrolment"])


class EnrolmentCurve(BaseModel):
    """`expected` is the plan; the gap to `actual` is what the lag alert fires on."""

    study_id: str
    target: int
    labels: list[str]
    actual: list[int]
    expected: list[int]


@router.get("/{study_id}", response_model=EnrolmentCurve, summary="Enrolment vs plan")
def enrolment_curve(study_id: str) -> EnrolmentCurve:
    """Phase 2 (Roxy): real S-curve from generated subjects. Phase 0: straight-line stub."""
    study = loader.find("studies", "id", study_id)
    if study is None:
        raise HTTPException(status_code=404, detail=f"No study {study_id}")

    target, actual_total = study["target_enrolment"], study["actual_enrolment"]
    labels = ["Mar", "Apr", "May", "Jun", "Jul", "Aug"]
    n = len(labels)
    actual = [round(actual_total * (i + 1) / n) for i in range(n)]
    expected = [round(target * 0.75 * (i + 1) / n) for i in range(n)]
    return EnrolmentCurve(
        study_id=study_id, target=target, labels=labels, actual=actual, expected=expected
    )
