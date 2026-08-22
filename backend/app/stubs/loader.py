"""STUB_MODE fixture loader. OWNER: Kavin.

Resolution order for any dataset:

  1. contracts/fixtures/<name>.json   — Roxy's generated portfolio, once it lands
  2. backend/app/stubs/seed.py        — a tiny hardcoded seed so Phase 0 works today

That ordering means the API is live now AND upgrades itself the moment Roxy runs
`python -m datagen.run --out contracts/fixtures/` — no code change, no coordination.

frontend/mocks/ is generated from the SAME fixture directory, so the two cannot drift
in shape. That is what stops integration dying at hour 20.
"""

import json
from functools import lru_cache
from pathlib import Path

from . import seed

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"


@lru_cache
def load(name: str) -> list | dict:
    """Load dataset `name`, preferring generated fixtures over the hardcoded seed."""
    path = FIXTURES_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    return seed.SEED.get(name, [])


def source_of(name: str) -> str:
    """Which source answered — surfaced on /health so nobody guesses at 3am."""
    return "fixtures" if (FIXTURES_DIR / f"{name}.json").exists() else "seed"


def find(name: str, key: str, value: str) -> dict | None:
    """First record in dataset `name` where record[key] == value."""
    return next((r for r in load(name) if r.get(key) == value), None)
