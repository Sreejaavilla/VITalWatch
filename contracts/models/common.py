"""Shared primitives. OWNER: Kavin.

Every model in this package inherits CTMSModel so serialisation behaves identically
across the API, the fixtures and the audit trail. Don't subclass BaseModel directly.
"""

from datetime import date, datetime, timezone
from pydantic import BaseModel, ConfigDict


class CTMSModel(BaseModel):
    """Base for every contract model.

    `use_enum_values=False` keeps enums as enums in Python and serialises them to
    their string value in JSON — so the frontend sees "enrolling", not an int.
    """

    model_config = ConfigDict(
        use_enum_values=False,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",  # a typo'd field name fails loudly at hour 3, not silently at hour 20
    )


def utcnow() -> datetime:
    """Server clock, always UTC, always timezone-aware.

    Audit timestamps and reporting deadlines are computed from this and NEVER from a
    client-supplied value. ALCOA+ 'contemporaneous' depends on it.
    """
    return datetime.now(timezone.utc)


__all__ = ["CTMSModel", "utcnow", "date", "datetime"]
