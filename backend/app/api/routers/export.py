"""/api/export — CDISC-shaped exports. OWNER: Roxy. Phase 4.

Shaping logic belongs in datagen/cdisc/ so it runs standalone.
PHASE 0 PLACEHOLDER: headers only, no rows.

RBAC acceptance (Caleb, Phase 1): a study_coordinator token gets 403 here;
a regulator token gets 200. That pair is the named test in the roadmap.
"""

from fastapi import APIRouter, HTTPException, Response

router = APIRouter(prefix="/api/export", tags=["export"])

SDTM_COLUMNS = {
    "DM": ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "SITEID", "AGE", "SEX", "ARM", "RFSTDTC"],
    "AE": ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AEDECOD", "AESEV",
           "AESER", "AESTDTC", "AEOUT", "AEREL"],
}


@router.get("/sdtm", summary="SDTM-shaped domain export (DM or AE only)")
def export_sdtm(domain: str = "DM") -> Response:
    """Two domains only. Full SDTM/ADaM is explicitly deferred — see ROADMAP."""
    domain = domain.upper()
    if domain not in SDTM_COLUMNS:
        raise HTTPException(status_code=400, detail="domain must be DM or AE")
    csv = ",".join(SDTM_COLUMNS[domain]) + "\n"
    return Response(
        content=csv,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{domain.lower()}.csv"'},
    )


@router.get("/define-xml", summary="Define-XML stub describing DM and AE")
def export_define_xml() -> Response:
    """PLACEHOLDER. Roxy: describe both domains. Not a valid full Define-XML 2.1 package."""
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<ODM><!-- stub: DM, AE --></ODM>\n'
    return Response(content=xml, media_type="application/xml")
