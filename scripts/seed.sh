#!/usr/bin/env bash
# Rebuild the synthetic portfolio from scratch.
# This is the demo-recovery plan: if the data gets into a strange state on stage,
# run this and restart. The generator is seeded, so the portfolio comes back identical.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -f data/ctms.db
.venv/bin/python -m app.db
