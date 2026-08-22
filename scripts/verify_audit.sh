#!/usr/bin/env bash
# Walk the audit hash chain and print OK, or the sequence number where it broke.
# A demo prop: tamper with a row, run this, and watch it name the row.
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m app.audit
