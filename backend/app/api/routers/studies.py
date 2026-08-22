"""/api/studies. OWNER: Kavin."""

from fastapi import APIRouter, HTTPException

from contracts.models import Study
from ...stubs import loader

router = APIRouter(prefix="/api/studies", tags=["studies"])


@router.get("", response_model=list[Study], summary="List studies in the portfolio")
def list_studies() -> list[Study]:
    """Phase 2 (Caleb): scope by role — PI sees own, coordinator sees own sites."""
    return [Study(**s) for s in loader.load("studies")]


@router.get("/{study_id}", response_model=Study, summary="One study")
def get_study(study_id: str) -> Study:
    """404 rather than 403 when outside the caller's scope — don't leak existence."""
    record = loader.find("studies", "id", study_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No study {study_id}")
    return Study(**record)
