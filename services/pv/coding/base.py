"""CodingService protocol — the drop-in swap point. OWNER: Sreeja.

Every implementation returns the same shape, so swapping a licensed dictionary in
touches exactly one line of wiring.
"""


class CodingService:
    """Protocol. Implementations: MockCodingService, FaissCodingService, MedDRACodingService."""

    def code(self, narrative, top_k=3):
        """free text -> [{term, code, level: 'LLT'|'PT', score}], best first."""
        raise NotImplementedError

    def code_drug(self, drug_text, top_k=3):
        """free text -> [{drug_name, atc_or_code, score}]. WHODrug's stand-in."""
        raise NotImplementedError
