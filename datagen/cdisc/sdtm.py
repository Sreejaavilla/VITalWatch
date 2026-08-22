"""SDTM-shaped domain export. OWNER: Roxy. Phase 4.

Two domains only — DM and AE. That demonstrates the pattern; completeness is a
data-management exercise measured in weeks, and is explicitly deferred.

DM: STUDYID DOMAIN USUBJID SUBJID SITEID AGE SEX ARM RFSTDTC
AE: STUDYID DOMAIN USUBJID AESEQ AETERM AEDECOD AESEV AESER AESTDTC AEOUT AEREL
"""


def export_dm(subjects, studies):
    raise NotImplementedError


def export_ae(aes):
    raise NotImplementedError
