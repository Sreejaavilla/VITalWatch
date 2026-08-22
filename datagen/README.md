# Data generator — Roxy

```bash
python -m datagen.run --out contracts/fixtures/ --seed 1947   # fixtures for STUB_MODE
python -m datagen.seed                                        # load Supabase (needs DATABASE_URL)
python -m datagen.cdisc.sdtm --domain DM --out datagen/out/
python -m datagen.cdisc.fhir --resource ResearchStudy --id STU-001
```

**Fixed seed = reproducible demo.** The numbers on stage must match the numbers in
the deck and the numbers in the recorded video. Never regenerate with a new seed
after Phase 3 freeze.

## Target shape of the portfolio

8 studies across phases · 12 sites · ~400 subjects · ~30 deviations · ~50 AEs (6 serious)

The portfolio must tell a story, not just fill tables:
* **two studies deliberately lagging** target enrolment → the enrolment-lag alert has something to fire on
* **one study with EC approval expiring inside 30 days** → the ethics-renewal alert fires
* **at least three overdue monitoring visits** → that KPI is non-zero
* **one AE term over-represented in a single study arm** → the DSMB signal view has a signal
* **a realistic S-curve** on enrolment, not a straight line — judges have seen real curves
