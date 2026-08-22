"""MedDRA / WHODrug adapter. OWNER: Sreeja. INTENTIONALLY UNIMPLEMENTED.

MedDRA (MSSO) and WHODrug (UMC) are licensed commercial dictionaries and cannot be
distributed with or obtained for this build. This class exists to make the swap point
concrete: drop in the licensed files, implement these two methods, change one line in
the service factory. Nothing else in the system moves.

This file is deliberate scope deferral, not an unfinished feature.
"""


class MedDRACodingService:
    def code(self, narrative, top_k=3):
        raise NotImplementedError("Requires a licensed MedDRA subscription.")

    def code_drug(self, drug_text, top_k=3):
        raise NotImplementedError("Requires a licensed WHODrug subscription.")
