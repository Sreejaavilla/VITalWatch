# Fixtures — the anti-drift device

OWNER: Roxy generates them, everyone reads them.

`backend/app/stubs/` (STUB_MODE) and `frontend/mocks/` both load from this directory.
They cannot drift in *shape*, only in freshness. If you hand-edit a file here,
regenerate instead: `python -m datagen.run --out contracts/fixtures/ --seed 1947`

Expected files: studies.json sites.json subjects.json visits.json deviations.json
queries.json adverse_events.json milestones.json audit_events.json users.json
kpi_portfolio.json alerts.json signals.json
