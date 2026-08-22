"""CDISC SDTM export — the DM (Demographics) domain.

One domain, not a submission package. That is the honest scope and it should be stated
rather than implied: a full SDTM/ADaM deliverable is dozens of domains, controlled
terminology, Define-XML metadata and a reviewer's guide. What one domain demonstrates is
the thing worth demonstrating — that the data model already carries what a submission
needs, and that producing it is a mapping rather than a re-collection.

Variable names and roles follow the SDTM Implementation Guide for DM. Where our data
cannot fill a required variable, the column is present and empty rather than absent:
a missing column breaks a downstream reader, whereas an empty one is simply missing data,
which is a condition every submission pipeline already handles.
"""

from __future__ import annotations

import csv
import io
from .db import Connection, Row  # driver-neutral: SQLite or Postgres
from collections.abc import Iterator

#: DM variables in submission order. `AGE` is deliberately absent and `AGEGR1` carries
#: the information instead: we store an age *band*, never an exact age, because an exact
#: age is a re-identification vector and DPDP data minimisation says do not collect what
#: you do not need. Submitting `AGEGR1` is the correct expression of that choice, not a
#: workaround for missing data.
COLUMNS = (
    "STUDYID",   # Study identifier
    "DOMAIN",    # Domain abbreviation — always "DM"
    "USUBJID",   # Unique subject identifier, unique across the whole submission
    "SUBJID",    # Subject identifier within the study
    "SITEID",    # Study site identifier
    "AGEGR1",    # Pooled age group (see note above)
    "SEX",       # Sex
    "ARM",       # Description of the planned arm
    "ARMCD",     # Planned arm code
    "COUNTRY",   # Country, ISO 3166-1 alpha-3
    "RFSTDTC",   # Subject reference start date — first exposure, ISO 8601
    "RFENDTC",   # Subject reference end date
    "DMDTC",     # Date of demographic collection
)

#: ARM is free text in our schema; ARMCD is a short controlled code. Mapping them
#: explicitly beats truncating ARM to eight characters and hoping.
ARM_CODES = {"Trial drug": "TRT", "Control": "CTL"}


def _row(subject: Row, study_id: str) -> dict[str, str]:
    arm = subject["arm"] or ""
    return {
        "STUDYID": study_id,
        "DOMAIN": "DM",
        # USUBJID must be unique across the submission, not just within a study. The
        # subject code already carries its study, so it qualifies as-is.
        "USUBJID": subject["subject_code"],
        "SUBJID": subject["subject_code"].rsplit("-", 1)[-1],
        "SITEID": subject["site_id"],
        "AGEGR1": subject["age_band"] or "",
        "SEX": subject["sex"] or "U",  # SDTM controlled terminology: U = unknown
        "ARM": arm,
        "ARMCD": ARM_CODES.get(arm, ""),
        "COUNTRY": "IND",
        # RFSTDTC is first exposure. A screen failure was never exposed, so it is
        # correctly empty rather than backfilled with the screening date.
        "RFSTDTC": subject["enrolled_date"] or "",
        "RFENDTC": "",
        "DMDTC": subject["screened_date"] or "",
    }


def dm_rows(conn: Connection, study_id: str | None = None) -> Iterator[str]:
    """Yield the DM domain as CSV text, one row at a time.

    Streamed rather than assembled in memory. At 392 subjects that is unnecessary; at
    submission scale it is the difference between an export and an outage, and the
    streaming version is no harder to write.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")

    def flush() -> str:
        value = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return value

    writer.writeheader()
    yield flush()

    sql = "SELECT * FROM subjects"
    params: tuple = ()
    if study_id:
        sql += " WHERE study_id = ?"
        params = (study_id,)
    sql += " ORDER BY study_id, subject_code"

    for subject in conn.execute(sql, params):
        writer.writerow(_row(subject, subject["study_id"]))
        yield flush()


if __name__ == "__main__":
    import sys

    from .db import connect

    study = sys.argv[1] if len(sys.argv) > 1 else None
    sys.stdout.writelines(dm_rows(connect(), study))
