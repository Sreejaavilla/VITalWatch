"""/api/fhir — HL7 FHIR R4 resources. OWNER: Roxy. Phase 4.

Interoperability is demonstrated by CONFORMANT STRUCTURE, not by a live connection to
an EDC, hospital information system or ABDM — those need partner credentials that do
not exist at a hackathon. Explicitly deferred, and said out loud on the slide.

PHASE 0 PLACEHOLDER: minimal valid-shaped resources built from the seeded study.
"""

from fastapi import APIRouter, HTTPException

from ...stubs import loader

router = APIRouter(prefix="/api/fhir", tags=["fhir"])

_PHASE_DISPLAY = {"I": "Phase 1", "II": "Phase 2", "III": "Phase 3", "IV": "Phase 4"}


@router.get("/ResearchStudy/{study_id}", summary="FHIR R4 ResearchStudy")
def research_study(study_id: str) -> dict:
    study = loader.find("studies", "id", study_id)
    if study is None:
        raise HTTPException(status_code=404, detail=f"No study {study_id}")
    return {
        "resourceType": "ResearchStudy",
        "id": study["id"],
        "identifier": [{"system": "https://ctri.nic.in", "value": study.get("ctri_number")}],
        "title": study["title"],
        "status": "active" if study["status"] == "enrolling" else "administratively-completed",
        "phase": {"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/research-study-phase",
            "code": study["phase"].lower(),
            "display": _PHASE_DISPLAY.get(study["phase"], study["phase"]),
        }]},
    }


@router.get("/AdverseEvent/{ae_id}", summary="FHIR R4 AdverseEvent")
def adverse_event(ae_id: str) -> dict:
    ae = loader.find("adverse_events", "id", ae_id)
    if ae is None:
        raise HTTPException(status_code=404, detail=f"No adverse event {ae_id}")
    return {
        "resourceType": "AdverseEvent",
        "id": ae["id"],
        "actuality": "actual",
        "subject": {"identifier": {"value": ae["subject_code"]}},
        "date": ae["reported_at"],
        "seriousness": {"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/adverse-event-seriousness",
            "code": "serious" if ae.get("serious") else "non-serious",
        }]},
        "event": {"text": ae.get("coded_term") or ae["narrative"]},
    }
