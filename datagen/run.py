"""Generate the full synthetic portfolio into contracts/fixtures/. OWNER: Roxy.

    python -m datagen.run --out contracts/fixtures/ --seed 1947

Phase 0 writes: studies.json, sites.json, subjects.json, milestones.json,
enrolment.json. Visits, deviations, queries and AEs are Phase 1 (generators/events.py).

STRICT DEPENDENCY: every payload is validated against contracts.models before it
is written. If Kavin's models are not implemented yet, this exits with a clear
message instead of emitting unvalidated JSON — the fixtures ARE the contract.
"""

import argparse
import json
import random
import sys
from pathlib import Path

from datagen.generators import enrolment, studies as gen_studies


def _load_models():
    try:
        from contracts.models import Study, Site, Subject, Milestone
    except (ImportError, NotImplementedError) as e:
        print(
            "BLOCKED: contracts.models is not implemented yet.\n"
            "  This is Kavin's Phase 0 task; datagen validates every fixture against\n"
            "  those models before writing (the fixtures ARE the shared contract).\n"
            f"  Underlying error: {e}\n"
            "  No files were written.",
            file=sys.stderr,
        )
        sys.exit(1)
    return {"Study": Study, "Site": Site, "Subject": Subject, "Milestone": Milestone}


def _validate(models, name, rows):
    model = models[name]
    for i, row in enumerate(rows):
        try:
            model.model_validate(row)
        except Exception as e:
            print(f"VALIDATION FAILED: {name}[{i}] ({row.get('id', '?')}): {e}", file=sys.stderr)
            sys.exit(1)


def generate(seed):
    models = _load_models()
    rng = random.Random(seed)

    sites = gen_studies.make_sites(12, rng)
    study_rows = gen_studies.make_studies(8, rng)
    gen_studies.assign_pis_and_sites(study_rows, sites, rng)

    milestones = []
    for s in study_rows:
        milestones.extend(gen_studies.make_milestones(s, rng))

    curves = enrolment.build_curves(study_rows, seed=seed)

    subjects = []
    subject_rng = random.Random(f"{seed}:subjects")
    active_sites = [s for s in sites if s["status"] == "activated"]
    for s in study_rows:
        subjects.extend(enrolment.make_subjects(s, active_sites, subject_rng))

    to_write = [
        ("studies.json", "Study", study_rows),
        ("sites.json", "Site", sites),
        ("milestones.json", "Milestone", milestones),
        ("subjects.json", "Subject", subjects),
        # plain chart data; openapi: GET /api/enrolment/{id} -> {actual[], expected[], target}
        ("enrolment.json", None, curves),
    ]

    for _, model_name, rows in to_write:
        if model_name:
            _validate(models, model_name, rows)
    return {filename: rows for filename, _, rows in to_write}


def main():
    parser = argparse.ArgumentParser(description="Generate the synthetic AIIA portfolio.")
    parser.add_argument("--out", default="contracts/fixtures/", help="output directory")
    parser.add_argument("--seed", type=int, default=1947, help="fixed demo seed")
    parser.add_argument("--studies", type=int, default=8)
    parser.add_argument("--sites", type=int, default=12)
    args = parser.parse_args()

    payloads = generate(args.seed)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, rows in payloads.items():
        (out_dir / filename).write_text(json.dumps(rows, indent=2) + "\n")

    n_subjects = len(payloads["subjects.json"])
    print(f"Wrote {len(payloads)} fixture files to {args.out} (seed={args.seed})")
    print(f"  studies={len(payloads['studies.json'])} sites={len(payloads['sites.json'])} "
          f"subjects={n_subjects} milestones={len(payloads['milestones.json'])}")


if __name__ == "__main__":
    main()
