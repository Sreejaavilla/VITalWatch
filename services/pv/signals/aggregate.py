"""Safety signal aggregation for the DSMB. OWNER: Sreeja.

Phase 2: counts by coded term x study x severity, ranked.
Phase 4: observed vs expected disproportionality so a term over-represented in one
arm surfaces above a term that is merely common.
"""


def by_term(aes, study_id=None):
    """-> [{term, count, serious_count, studies[], severity_breakdown}] ranked."""
    raise NotImplementedError


def disproportionality(aes):
    """Phase 4. Observed vs expected per term. Cuttable — raw counts still demo."""
    raise NotImplementedError
