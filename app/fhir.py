"""HL7 FHIR R4 resource shapes.

**This is structure, not integration, and the difference matters.** A `ResearchStudy`
resource served from our own database and consumed by nobody proves that the data maps
onto the standard; it does not prove interoperability, which requires a counterparty
system, credentials and a conformance test we do not have at a hackathon. Say the
smaller true thing.

What the mapping does establish is that the model was not invented in isolation:
study status, phase, condition, sponsor, principal investigator and study identifiers
all have a defined home in FHIR, and ours land in them without contortion. Registration
identifiers use the CTRI namespace, which is the India-specific part of this and the
part a generic FHIR example will not show you.
"""

from __future__ import annotations

import sqlite3

#: Our study lifecycle to the FHIR R4 `ResearchStudy.status` value set. FHIR's vocabulary
#: is narrower than ours, so several of our stages collapse into `active`. Collapsing is
#: correct; inventing a code outside the value set would make the resource non-conformant,
#: which defeats the point of emitting one.
STATUS_MAP = {
    "protocol": "draft",
    "ec_approval": "approved",
    "ctri_registered": "approved",
    "site_activation": "approved",
    "screening": "active",
    "enrolling": "active",
    "follow_up": "active",
    "close_out": "completed",
}

#: `ResearchStudy.phase`, from the FHIR-defined code system. Observational studies have
#: no phase in the trial sense; FHIR expresses that as `n-a` rather than as an omission.
PHASE_MAP = {
    "I": "phase-1", "II": "phase-2", "III": "phase-3", "IV": "phase-4",
    "observational": "n-a",
}


def research_study(study: sqlite3.Row) -> dict:
    """One study as a FHIR R4 `ResearchStudy`."""
    resource: dict = {
        "resourceType": "ResearchStudy",
        "id": study["id"],
        "meta": {
            "profile": ["http://hl7.org/fhir/StructureDefinition/ResearchStudy"],
            # Synthetic provenance travels with the resource. If this were ever exported
            # into another system, the tag is what stops it being mistaken for real data.
            "tag": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActReason",
                "code": "HTEST",
                "display": "test health data",
            }],
        },
        "identifier": [{
            "use": "official",
            "system": "https://vitalwatch.aiia.in/protocol",
            "value": study["protocol_no"],
        }],
        "title": study["title"],
        "status": STATUS_MAP.get(study["status"], "active"),
        "primaryPurposeType": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/research-study-prim-purp-type",
                "code": "treatment",
            }]
        },
        "condition": [{"text": study["therapeutic_area"]}],
        "principalInvestigator": {"display": study["pi_name"]},
        "sponsor": {"display": "All India Institute of Ayurveda"},
        "period": {k: v for k, v in
                   (("start", study["start_date"]), ("end", study["end_date"])) if v},
        "enrollment": [{
            "display": f"{study['actual_enrolment']} enrolled of {study['target_enrolment']} target"
        }],
    }

    phase = PHASE_MAP.get(study["phase"])
    if phase:
        resource["phase"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/research-study-phase",
                "code": phase,
                "display": study["phase"],
            }]
        }

    # CTRI registration as a secondary identifier. This is the India-specific piece:
    # a generic FHIR ResearchStudy example carries ClinicalTrials.gov, not CTRI.
    if study["ctri_number"]:
        resource["identifier"].append({
            "use": "secondary",
            "type": {"text": "Clinical Trials Registry - India"},
            "system": "https://ctri.nic.in",
            "value": study["ctri_number"],
        })

    return resource


if __name__ == "__main__":
    import json
    import sys

    from .db import connect

    study_id = sys.argv[1] if len(sys.argv) > 1 else "STU-001"
    row = connect().execute("SELECT * FROM studies WHERE id = ?", (study_id,)).fetchone()
    if row is None:
        print(f"no study {study_id}")
        raise SystemExit(1)
    print(json.dumps(research_study(row), indent=2))
