# Frontend — Ishan

```bash
npm install
NEXT_PUBLIC_STUB_MODE=true npm run dev     # runs with the backend completely down
```

**Develop against stub mode.** `lib/api.ts` is the only place that decides whether a
call hits the API or reads `mocks/`. No component ever fetches directly — if one does,
stub mode stops working and the stage fallback dies with it.

`mocks/` is generated from `contracts/fixtures/`. Never hand-edit it:
```bash
npm run sync-mocks
```

## Screens (the demo click path, in order)

1. `/login` — role picker → JWT → redirect by role claim
2. `/portfolio` — 6 KPI tiles, study grid, alert banner
3. `/study/[id]` — enrolment vs target, sites, visit compliance, deviations, queries, milestones
4. `/ae` — AE intake form, coding suggestions, reporting-timeline countdown, DSMB signal table
5. `/audit` — chronological trail with actor, role, action, before/after; "verify chain" button
6. `/alerts` — severity-ranked, deep-links into the offending study

## Roles

Seven roles, seven default landing screens. If the clock runs out, demo four
(PI, coordinator, PV, regulator) and slide the rest — see the cut list in ROADMAP.md.
