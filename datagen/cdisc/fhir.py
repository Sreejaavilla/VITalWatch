"""HL7 FHIR R4 resource shaping. OWNER: Roxy. Phase 4. Cut candidate #1.

Interoperability is proven by CONFORMANT STRUCTURE, not by a live connection to an
EDC, hospital information system or ABDM — those need partner systems and credentials
that do not exist at a hackathon. Explicitly deferred, stated on the slide.

Acceptance: paste the output into any online FHIR R4 validator and it passes.
"""


def research_study(study):
    """-> FHIR R4 ResearchStudy: resourceType, id, identifier (CTRI), title, status, phase."""
    raise NotImplementedError


def adverse_event(ae):
    """-> FHIR R4 AdverseEvent: resourceType, id, subject, event (coding), seriousness,
    severity, date, suspectEntity."""
    raise NotImplementedError
