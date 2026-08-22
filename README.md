# VITalWatch — AIIA Clinical Trial Management + Pharmacovigilance

Real-time CTMS and monitoring dashboard for the All India Institute of Ayurveda,
with an integrated pharmacovigilance module for the NPvCC.

**Build plan, ownership and phase checklists live in [ROADMAP.md](./ROADMAP.md).**

> Demo system. Synthetic data only. No real patient data at any stage.

## Stack
FastAPI (Render) · Next.js (Vercel) · Supabase Postgres + Auth · Sentence Transformers + FAISS

## Stub mode
`STUB_MODE=true` runs the whole system on `contracts/fixtures/` — no database, no Supabase,
no ML model, no network. Every component below runs standalone in this mode.

## Run each piece standalone

### Backend — Kavin
```bash
cp .env.example .env
pip install -r backend/requirements.txt
STUB_MODE=true uvicorn backend.app.main:app --reload --port 8000
# http://localhost:8000/health  →  {"status":"ok","stub_mode":true}
# http://localhost:8000/docs    →  every endpoint, no DB required
```

### Frontend — Ishan
```bash
cd frontend && npm install
NEXT_PUBLIC_STUB_MODE=true npm run dev
# http://localhost:3000 — runs with the backend completely down
```

### Pharmacovigilance — Sreeja
```bash
python -m services.pv.cli code "patient reported a severe headache after dosing"
python -m services.pv.cli timeline --serious --onset 2026-08-20T09:00Z
```

### Data generator — Roxy
```bash
python -m datagen.run --out contracts/fixtures/ --seed 1947
python -m datagen.seed          # loads Supabase; needs DATABASE_URL
python -m datagen.cdisc.sdtm --domain DM --out datagen/out/
```

### Auth / audit — Caleb
```bash
psql "$DATABASE_URL" -f backend/app/db/schema.sql
python -m backend.app.db.seed_users
./scripts/verify_audit.sh       # walks the hash chain, prints OK or the broken index
```

## Roles
principal_investigator · study_coordinator · monitor · ethics_committee · pharmacovigilance · admin · regulator (read-only)
