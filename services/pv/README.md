# Pharmacovigilance — Sreeja

Runs standalone. No backend, no database, no network.

```bash
python -m services.pv.cli code "patient reported a severe headache after dosing"
python -m services.pv.cli timeline --serious --onset 2026-08-20T09:00Z
python -m services.pv.cli signals --study STU-003
```

## The dictionary question

**We do not have MedDRA or WHODrug.** They are licensed commercial dictionaries and
cannot be obtained for a hackathon build. What exists here is a curated ~200-term
subset behind a `CodingService` protocol, with `MedDRACodingService` as an
unimplemented stub against the same interface — so a licensed dictionary is a
one-class swap with no change anywhere else in the system.

Say this on the slide, unprompted. Owning it reads as rigour; being caught reads as bluffing.

## Coding backend

`PV_CODING_BACKEND=mock` — exact/fuzzy match on the CSV. No dependencies. Always works.
`PV_CODING_BACKEND=faiss` — Sentence Transformers embeddings + FAISS nearest-neighbour.

**Decision point, hour 8:** if `all-MiniLM-L6-v2` won't load in Render's free-tier RAM,
precompute term embeddings in Colab, commit the `.npy`, and ship only the query encoder.
If that also fails, fall back to `mock`. The interface does not change either way,
so nothing else in the system and nothing in the pitch has to change.
