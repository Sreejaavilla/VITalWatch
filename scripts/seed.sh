#!/usr/bin/env bash
# Rebuild the synthetic portfolio from scratch.
# This is the demo-recovery plan: if the data gets into a strange state on stage,
# run this and restart. The generator is seeded, so the portfolio comes back identical
# — including the audit chain head hash, on either engine.
set -euo pipefail
cd "$(dirname "$0")/.."

# Pick up DATABASE_URL from .env the same way the app does, so this script and the
# running application never disagree about which database they are talking to.
if [ -f .env ]; then set -a; . ./.env; set +a; fi

if [ -n "${DATABASE_URL:-}" ]; then
  echo "resetting Postgres — $(echo "$DATABASE_URL" | sed 's|.*@||; s|/.*||')"
  .venv/bin/python -m scripts.supabase reset
else
  rm -f data/ctms.db
  .venv/bin/python -m app.db
fi
