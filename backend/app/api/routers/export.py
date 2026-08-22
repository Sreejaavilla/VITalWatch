"""/api/export — CDISC-shaped exports. OWNER: Roxy. Phase 4.

Shaping logic lives in datagen/cdisc/ so it runs standalone.
"""


def export_sdtm(domain, user):
    """GET /api/export/sdtm?domain=DM|AE -> text/csv.

    DM columns: STUDYID DOMAIN USUBJID SUBJID SITEID AGE SEX ARM RFSTDTC
    Regulator and admin only — a coordinator token must get 403 here.
    """
    raise NotImplementedError


def export_define_xml(user):
    """GET /api/export/define-xml -> application/xml. Stub describing DM and AE only."""
    raise NotImplementedError
