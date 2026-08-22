"""Exact/fuzzy lookup over the curated term subset. OWNER: Sreeja.

Zero dependencies. This is the fallback that always works, including on stage.
"""


class MockCodingService:
    """Normalise, then exact match, then difflib fuzzy match against terms/*.csv."""

    def code(self, narrative, top_k=3):
        raise NotImplementedError

    def code_drug(self, drug_text, top_k=3):
        raise NotImplementedError
