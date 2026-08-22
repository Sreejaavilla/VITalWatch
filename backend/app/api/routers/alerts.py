"""/api/alerts. OWNER: Kavin."""

from fastapi import APIRouter, HTTPException

from contracts.models import Alert
from ...stubs import loader

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


@router.get("", response_model=list[Alert], summary="Severity-ranked alerts")
def list_alerts() -> list[Alert]:
    records = sorted(loader.load("alerts"), key=lambda a: _SEVERITY_ORDER.get(a["severity"], 9))
    return [Alert(**a) for a in records]


@router.post("/{alert_id}/ack", response_model=Alert, summary="Acknowledge an alert")
def acknowledge_alert(alert_id: str) -> Alert:
    """Phase 2 (Caleb): writes an audit event. Regulator role must get 403 here."""
    record = loader.find("alerts", "id", alert_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No alert {alert_id}")
    return Alert(**record)
