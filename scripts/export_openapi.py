"""Export the live OpenAPI spec to contracts/openapi.yaml. OWNER: Kavin.

    python scripts/export_openapi.py

The spec is GENERATED from the running app rather than hand-maintained, so it cannot
drift from what the API actually returns. Re-run it after any route change and commit
the result — that file is what Ishan reads.
"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.main import app  # noqa: E402

OUT = ROOT / "contracts" / "openapi.yaml"
HEADER = (
    "# GENERATED — do not hand-edit.\n"
    "# Regenerate:  python scripts/export_openapi.py\n"
    "# Source of truth is backend/app/api/routers/*.py + contracts/models/.\n"
)

if __name__ == "__main__":
    spec = app.openapi()
    OUT.write_text(HEADER + yaml.safe_dump(spec, sort_keys=False, allow_unicode=True))
    paths = sum(len(v) for v in spec["paths"].values())
    print(f"wrote {OUT.relative_to(ROOT)} — {len(spec['paths'])} paths, {paths} operations")
