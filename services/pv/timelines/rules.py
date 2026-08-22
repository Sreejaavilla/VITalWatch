"""Regulatory reporting clocks. OWNER: Sreeja.

New Drugs and Clinical Trials Rules 2019:
  * SAE reported to the Ethics Committee, the licensing authority and the sponsor
    within 24 hours of occurrence
  * Detailed narrative / analysis within 14 days of the SAE
Non-serious AEs are tracked in aggregate, not against a statutory clock.

Acceptance: an SAE filed with a past onset date shows status BREACHED with
hours_remaining negative. Deadlines are computed from the SERVER clock, never
from a client-supplied timestamp.
"""


def deadlines(onset_utc, serious):
    """-> {deadline_24h, deadline_14d} or None for non-serious."""
    raise NotImplementedError


def status(ae, now_utc):
    """-> 'on_track' | 'due_soon' | 'breached', plus hours_remaining."""
    raise NotImplementedError
