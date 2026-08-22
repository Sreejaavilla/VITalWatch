"""/api/fhir — HL7 FHIR R4 resources. OWNER: Roxy. Phase 4.

Interoperability is demonstrated by CONFORMANT STRUCTURE, not by a live connection
to an EDC, HIS or ABDM. Say that out loud in the pitch.
"""


def research_study(study_id, user):
    """GET /api/fhir/ResearchStudy/{id} -> FHIR R4 ResearchStudy JSON."""
    raise NotImplementedError


def adverse_event(ae_id, user):
    """GET /api/fhir/AdverseEvent/{id} -> FHIR R4 AdverseEvent JSON."""
    raise NotImplementedError
