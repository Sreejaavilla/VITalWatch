"""/api/sites. OWNER: Kavin."""

from fastapi import APIRouter

from contracts.models import Site
from ...stubs import loader

router = APIRouter(prefix="/api/sites", tags=["sites"])


@router.get("", response_model=list[Site], summary="List sites with activation status")
def list_sites(study_id: str | None = None) -> list[Site]:
    records = loader.load("sites")
    if study_id:
        records = [s for s in records if study_id in s.get("study_ids", [])]
    return [Site(**s) for s in records]
