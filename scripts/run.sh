#!/usr/bin/env bash
# Start VITalWatch. One process, one port, no other services required.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/uvicorn app.main:app --reload --port 8000
