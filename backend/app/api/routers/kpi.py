"""/api/kpi. OWNER: Kavin."""

from fastapi import APIRouter, HTTPException

from contracts.models import PortfolioKPI, StudyKPI, utcnow
from ...stubs import loader

router = APIRouter(prefix="/api/kpi", tags=["kpi"])


@router.get("/portfolio", response_model=PortfolioKPI, summary="Six headline numbers")
def portfolio_kpis() -> PortfolioKPI:
    """Phase 2: compute from Postgres. Signature does not change — that is the point."""
    studies = loader.load("studies")
    sites = loader.load("sites")
    aes = loader.load("adverse_events")
    return PortfolioKPI(
        generated_at=utcnow(),
        active_studies=sum(1 for s in studies if s["status"] in {"enrolling", "screening", "follow_up"}),
        enrolled_total=sum(s["actual_enrolment"] for s in studies),
        target_total=sum(s["target_enrolment"] for s in studies),
        sites_activated=sum(1 for s in sites if s["status"] == "activated"),
        sites_total=len(sites),
        open_queries=len(loader.load("queries")),
        overdue_monitoring_visits=sum(
            1 for v in loader.load("visits") if v.get("monitoring_visit") and v.get("status") == "overdue"
        ),
        open_saes=sum(1 for a in aes if a.get("serious") and a.get("outcome") != "recovered"),
    )


@router.get("/study/{study_id}", response_model=StudyKPI, summary="Per-study metrics")
def study_kpis(study_id: str) -> StudyKPI:
    study = loader.find("studies", "id", study_id)
    if study is None:
        raise HTTPException(status_code=404, detail=f"No study {study_id}")

    enrolled, target = study["actual_enrolment"], study["target_enrolment"]
    aes = [a for a in loader.load("adverse_events") if a["study_id"] == study_id]
    return StudyKPI(
        generated_at=utcnow(),
        study_id=study_id,
        enrolled=enrolled,
        target=target,
        enrolment_pct=0.0 if target == 0 else round(100 * enrolled / target, 1),
        expected_by_today=round(target * 0.75),
        screen_failure_rate=0.0,
        visit_compliance_pct=0.0,
        open_queries=0,
        open_query_ageing_days=0.0,
        deviation_rate_per_site=0.0,
        open_saes=sum(1 for a in aes if a.get("serious")),
        days_to_next_milestone=None,
        next_milestone=None,
    )
