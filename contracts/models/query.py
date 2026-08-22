"""DataQuery — a data-cleaning query raised against a data point. OWNER: Kavin.

`age_days` is computed, not stored: open-query ageing is a KPI and must not go stale
because someone forgot to recompute a column.
"""

from datetime import date
from enum import Enum

from .common import CTMSModel


class QueryStatus(str, Enum):
    OPEN = "open"
    ANSWERED = "answered"
    CLOSED = "closed"


class DataQuery(CTMSModel):
    id: str
    study_id: str
    site_id: str
    subject_code: str | None = None

    field: str
    question: str
    raised_date: date
    raised_by: str
    answered_date: date | None = None
    closed_date: date | None = None
    status: QueryStatus

    #: Days open as of the response. Server-computed; ignore anything a client sends.
    age_days: int = 0
