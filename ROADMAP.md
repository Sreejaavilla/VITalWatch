# VITalWatch — AIIA CTMS + Pharmacovigilance

**SIH · 24 hours · 6 people · zero budget · synthetic data only**

Stack: **FastAPI** (Render) · **Next.js** (Vercel) · **Supabase** (Postgres + Auth) · **Sentence Transformers + FAISS** (AE coding)
Auth: Supabase JWT, RBAC enforced in app layer. RLS written as a design artifact, not a runtime dependency.

# What we are solving

**AIIA runs a portfolio of Ayurveda clinical trials and hosts the National Pharmacovigilance Coordination Centre for ASU&H drugs. All of it is tracked in disconnected spreadsheets.**

Study status sits in one file, recruitment in another, milestones in a third, data queries in a
fourth, adverse events in a fifth — each owned by a different person, each updated on a different
day. Nobody can answer "how is the portfolio doing right now?" without days of manual
reconciliation, and by the time the answer arrives it is already stale.

Three things break as a result:

1. **Decisions arrive late.** A study falling behind on enrolment is visible only when someone
  opens the right spreadsheet and does the arithmetic — usually long after it started slipping.
2. **Regulatory deadlines get missed.** A serious adverse event must reach the Ethics Committee
  and the licensing authority within 24 hours under the New Drugs and Clinical Trials Rules 2019.
   A spreadsheet does not start a clock, and it does not chase anyone.
3. **There is no audit trail.** A spreadsheet cell can be changed by anyone, at any time, leaving
  no record of who changed it, when, or what it said before. That is a compliance failure on its
   own terms — ALCOA+ data integrity is not achievable in a file that can be silently edited.

Underneath all three is one missing thing: **a single, real-time, role-based, auditable view of
the study lifecycle.**

# How we solve it

One system covering the full lifecycle — protocol → Ethics Committee approval → CTRI registration
→ site activation → screening → enrolment against target → visit and deviation compliance → data
queries → milestones → close-out — with a pharmacovigilance module attached to it, because AIIA
hosts the NPvCC and safety reporting is not a separate concern from trial management.

Five mechanisms do the actual work:


| The problem                                     | The mechanism                                                                                                                                                           | Where it lives                                                    |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Status is scattered and stale                   | One Postgres schema behind one API; every screen computes from the same source                                                                                          | `contracts/`, `backend/app/services/`                             |
| Nobody notices a study slipping                 | A rule engine evaluating configurable thresholds — enrolment lag, EC/CTRI renewal due, monitoring visit overdue — surfaced as ranked alerts that deep-link to the study | `backend/app/services/alerts.py`                                  |
| Statutory reporting clocks are not tracked      | AE/SAE intake that starts a 24-hour and 14-day clock on submission and shows breach status                                                                              | `services/pv/timelines/`                                          |
| Free-text AEs cannot be aggregated into signals | Semantic coding of narratives to standard terms, then aggregation by term × study × severity for the DSMB                                                               | `services/pv/coding/`, `services/pv/signals/`                     |
| Anyone can see or change anything, invisibly    | Seven roles resolved from a declarative matrix, plus an append-only hash-chained audit trail where tampering is detectable and locatable                                | `contracts/roles.yaml`, `backend/app/auth/`, `backend/app/audit/` |


The last row is the technical heart of the pitch. Everything else a spreadsheet could theoretically
imitate with enough discipline; **an immutable audit trail and enforced role separation are things a
spreadsheet cannot structurally provide.** That is the argument.

## Two design decisions that shape everything

**Contracts before code.** `contracts/` is written and frozen in the first two hours — the data
model, the API surface, the RBAC matrix. Six people then build against it in parallel without
blocking each other. The alternative — everyone inventing their own field names and joining up at
hour 12 — is the single most common way a hackathon team ships nothing.

**Stub mode is architectural, not a hack.** `STUB_MODE=true` runs the entire system from
`contracts/fixtures/` with no database, no Supabase, no ML model and no network. It is what Ishan
develops against from hour 2, and it is the parachute if anything dies on stage. Backend stubs and
frontend mocks read the *same* fixture files, so the two cannot drift in shape.

# What lives where

Six people, six territories. Ownership maps to directories so that the only file two people would
otherwise both edit — `backend/app/main.py` — is written once at hour 0 and never touched again.

```
VITalWatch/
├─ contracts/              [Kavin]   Shared truth. Frozen hour 2. Everyone imports, nobody forks.
│  ├─ models/              [Kavin]   12 pydantic models — the data model, single source
│  ├─ fixtures/            [Roxy]    Canonical fake payloads; stub mode AND frontend mocks read these
│  ├─ openapi.yaml         [Kavin]   Every endpoint and response shape
│  └─ roles.yaml           [Caleb]   7 roles × resource × action RBAC matrix
├─ backend/                          FastAPI service, deploys to Render
│  ├─ app/main.py          [Kavin]   Router registration — written hour 0, never touched again
│  ├─ app/config.py        [Kavin]   STUB_MODE and env loading
│  ├─ app/api/routers/               One file per owner — the anti-merge-conflict device
│  ├─ app/auth/            [Caleb]   JWT verify, current_user, require_role dependency
│  ├─ app/audit/           [Caleb]   Hash-chained append-only writer + chain verifier
│  ├─ app/db/              [Caleb]   schema.sql, rls.sql, seed.sql, Supabase session
│  ├─ app/services/        [Kavin]   KPI computation, alert rule engine
│  ├─ app/stubs/           [Kavin]   Fixture-backed responses for STUB_MODE
│  └─ tests/                         test_<owner>_*.py, one file per owner
├─ services/pv/            [Sreeja]  Pharmacovigilance — standalone, runs without the backend
│  ├─ coding/              [Sreeja]  CodingService interface + FAISS/mock implementations
│  ├─ terms/               [Sreeja]  Curated PT/LLT and drug subset (CSV)
│  ├─ timelines/           [Sreeja]  NDCT Rules 2019 reporting clocks
│  └─ signals/             [Sreeja]  AE aggregation for the DSMB view
├─ datagen/                [Roxy]    Synthetic portfolio generator — standalone, no backend needed
│  ├─ generators/          [Roxy]    Studies, sites, enrolment curves, visits, deviations, AEs
│  ├─ cdisc/               [Roxy]    SDTM DM + AE shaping, Define-XML stub, FHIR R4 resources
│  └─ out/                 [Roxy]    Generated data; one snapshot committed, rest gitignored
├─ frontend/               [Ishan]   Next.js, deploys to Vercel
│  ├─ app/                 [Ishan]   login · portfolio · study/[id] · ae · audit · alerts
│  ├─ components/          [Ishan]   Charts, KPI tiles, tables, alert banners
│  ├─ lib/                 [Ishan]   Single API client; NEXT_PUBLIC_STUB_MODE flips to mocks/
│  └─ mocks/               [Ishan]   Generated from contracts/fixtures — never hand-edited
├─ docs/                   [Avanthika] Deck outline, compliance matrix, architecture, demo script, Q&A
└─ scripts/                [Kavin]   dev.sh, seed.sh, verify_audit.sh
```

### Why each top-level directory exists

- `**contracts/**` — the anti-drift device. It sits at the root rather than inside `backend/`
because the frontend, the data generator and the PV module all import it too. If a field name
changes here, it changes for everyone at once. This is the directory that makes six people
working in parallel possible.
- `**backend/**` — the only thing that talks to the database, and the only place RBAC and audit
are enforced. Routers are split one file per owner so merge conflicts are structurally impossible.
- `**services/pv/**` — a top-level package rather than a backend subfolder, so Sreeja can build,
test and demo the whole pharmacovigilance flow with the backend, the database and the frontend
all down. Its routers are thin wrappers Kavin can stub if it isn't ready.
- `**datagen/**` — same reasoning for Roxy. It also carries the CDISC and FHIR shaping logic,
because that is data-format work, not API work.
- `**frontend/**` — one owner, no collisions. `lib/api.ts` is the only file that knows whether a
call hits the API or reads mocks; no component fetches directly, which is what keeps stub mode
working.
- `**docs/**` — the compliance matrix, deck and Q&A prep. Deliberately a *document* territory and
not a sprint: the ten-plus regulations in the problem statement are answered on paper, and only
the four genuinely buildable in 24 hours (audit trail, RBAC, pseudonymisation, reporting
timelines) are built.
- `**scripts/**` — `verify_audit.sh` is a demo prop as much as a tool. Tampering with a row on
stage and having the chain name the broken row is the strongest fifteen seconds of the pitch.

---

## The one thing that matters

**At hour 6 the team is demo-ready.** Everything after hour 6 is improvement, not survival.
**At hour 15 there is a hard freeze and a recorded video.** Non-negotiable.
Any component not demoable by hour 15 is cut, not finished.

## Ownership — nobody works on two components at once


| Who           | Component                                                  | Directory                                                                                                  |
| ------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Kavin**     | Contracts, API layer, KPI/alerts, integration, deploy      | `contracts/`, `backend/app/{main,config,api/routers/[studies,sites,enrolment,kpi,alerts]},services,stubs}` |
| **Caleb**     | Auth, RBAC, immutable audit trail, DB schema               | `backend/app/{auth,audit,db}`, `backend/app/api/routers/{auth,users,audit}.py`                             |
| **Ishan**     | All 7 role dashboards, drill-down, alerts UI, demo flow    | `frontend/`                                                                                                |
| **Roxy**      | Synthetic portfolio generator, CDISC/FHIR shaping          | `datagen/`, `backend/app/api/routers/{export,fhir}.py`                                                     |
| **Sreeja**    | Pharmacovigilance: AE/SAE intake, semantic coding, signals | `services/pv/`, `backend/app/api/routers/{ae,signals}.py`                                                  |
| **Avanthika** | Deck, compliance matrix, Q&A defence, demo script          | `docs/`                                                                                                    |


---

# Phase 0 — Contracts and skeleton · Hours 0–2

Nothing here is optional. After this nobody blocks anybody.

- [x] **[Kavin]** Push the scaffolded tree to `main`. Everyone clones and confirms `git log` shows it. ⛔ blocks: **everything**
- [x] **[Kavin]** Write all 12 models in `contracts/models/`. Verify: `python -c "from contracts.models import Study, Site, Subject, Visit, Deviation, DataQuery, AdverseEvent, Milestone, AuditEvent, User, KPISnapshot, Alert"` exits 0. ⛔ blocks: every backend and frontend task
- [x] **[Kavin]** `contracts/openapi.yaml` lists every endpoint with its response shape. Verify: Ishan can name the endpoint behind each of his 6 screens without asking.
- [x] **[Kavin]** `backend/app/main.py` registers all 12 routers. Verify: `GET /health` returns `200 {"status":"ok","stub_mode":true}` on the **Render URL**, not localhost. ⛔ blocks: Phase 3 video
- [ ] **[Kavin]** Vercel frontend fetches Render `/health` successfully across CORS. Verify: the deployed page prints the backend's JSON. ⛔ blocks: everything at hour 22
- [x] **[Caleb]** `contracts/roles.yaml` — 7 roles × resource × action matrix, including which roles may *never* see subject-identifying fields.
- [ ] **[Caleb]** Supabase project created, 7 demo users seeded (one per role), `POST /auth/login` returns a JWT carrying a `role` claim. Verify: decode the token, see the role.
- [ ] **[Caleb]** `backend/app/db/schema.sql` covers studies, sites, subjects, visits, deviations, queries, aes, milestones, audit_events, users. Verify: it applies against Supabase with no errors.
- [ ] **[Roxy]** `datagen` emits 8 studies + sites + enrolment curves into `contracts/fixtures/`. Verify: `python -m datagen.run --out contracts/fixtures/` produces valid JSON that imports as `contracts.models`. ⛔ blocks: stub mode looking real
- [ ] **[Sreeja]** `services/pv/terms/` holds ~200 curated PT/LLT rows and ~40 drug rows, CSV, with the `CodingService` interface signature written (not implemented).
- [ ] **[Ishan]** Next.js on Vercel with routes existing (blank is fine) for: `/login`, `/portfolio`, `/study/[id]`, `/ae`, `/audit`, `/alerts`.
- [ ] **[Rackshitha]** `docs/compliance-matrix.md` has every regulation listed as a row with an empty "where addressed" column. Filling it is Phase 2.

> ### 🚪 GATE — Hour 2: CONTRACTS FROZEN
>
> **Pass:** all 12 models import · openapi.yaml covers all 6 screens · Render `/health` green from the public URL · Supabase login returns a role-bearing JWT.
> **Fail branch:** delete FHIR, SDTM export and Define-XML from `contracts/` **right now** and freeze the smaller surface. Do not carry an unfrozen contract into Phase 1 — that is how integration dies at hour 20.
> After this gate, a breaking contract change requires saying it out loud to the whole room.

---

# Phase 1 — Walking skeleton · Hours 2–6

Every screen reachable, every endpoint returning fixture data. **Demo-ready at hour 6.**

- [ ] **[Kavin]** `STUB_MODE=true` makes all 12 routers return payloads read from `contracts/fixtures/`. Verify: `curl $RENDER/api/studies` returns 8 studies with no database configured.
- [ ] **[Kavin]** `/api/studies`, `/api/studies/{id}`, `/api/sites`, `/api/enrolment/{study_id}` live and stubbed.
- [ ] **[Kavin]** `/api/kpi/portfolio` returns the 6 headline KPIs hardcoded: studies active, total enrolled vs target, sites activated, open queries, overdue monitoring visits, open SAEs.
- [ ] **[Caleb]** `require_role()` dependency exists and is applied to every router. Verify: **a coordinator-role token returns 403 on `GET /api/export/sdtm`; a regulator token returns 200.** ⛔ blocks: nothing, but it is the pitch's spine
- [ ] **[Caleb]** `/api/audit` returns a stubbed list of audit events with actor, role, action, resource, timestamp, before/after.
- [ ] **[Ishan]** Login screen posts to `/auth/login`, stores the JWT, redirects by role claim. Verify: logging in as PV lands on a different default screen than logging in as regulator.
- [ ] **[Ishan]** Portfolio grid renders live from `/api/kpi/portfolio` + `/api/studies`. Verify: changing a fixture value changes the deployed page.
- [ ] **[Ishan]** Study drill-down shows enrolment vs target, site table, visit compliance, deviations, query counts, milestone timeline. Stubbed values are fine.
- [ ] **[Ishan]** AE report form posts to `/api/ae` and the audit page renders `/api/audit`. ⛔ blocks: the demo click path
- [ ] **[Sreeja]** `POST /api/ae` accepts an AE payload and echoes it back with a fake coded term and a computed reporting deadline.
- [ ] **[Roxy]** `datagen` now produces visits, protocol deviations, data queries, milestones and AEs — enough that the portfolio looks like a real institute, not lorem ipsum.
- [ ] **[Rackshitha]** Demo script v1 written: the exact click path, who narrates which screen, 4 minutes.

> ### 🚪 GATE — Hour 6: WALKING SKELETON
>
> **Pass:** on the **deployed URLs**, one person clicks login → portfolio → study drill-down → file an AE → see it in the audit log, without a crash.
> **Fail branch:** stop all Phase 2 work. Every person joins the click path until it completes. A team with a working skeleton at hour 8 and nothing else still has a demo; a team with four half-built subsystems at hour 15 does not.

---

# Phase 2 — Replace the stubs · Hours 6–15

`STUB_MODE=false` becomes the default. This is where the pitch gets its substance.

### Data + audit (the technical heart)

- [ ] **[Caleb]** Audit trail is **append-only and hash-chained**: each row stores `prev_hash` and `hash(payload + prev_hash)`. Verify: `scripts/verify_audit.sh` walks the chain and prints OK; manually `UPDATE` one row and it prints the exact broken index. ⛔ blocks: the strongest 30 seconds of the pitch
- [ ] **[Caleb]** Every mutating endpoint writes an audit event with actor, role, action, resource id, before-value, after-value, UTC timestamp. Verify: file an AE, then find that exact event in `/api/audit` with both values populated.
- [ ] **[Caleb]** RBAC enforced on all 12 routers from `roles.yaml`, not hardcoded per-route. Verify: a table test asserting all 7 roles × 12 routers returns the matrix's expected status code.
- [ ] **[Caleb]** Read-only regulator role cannot mutate anything. Verify: regulator token gets 403 on every POST/PATCH/DELETE in the app.
- [ ] **[Caleb]** Subject records expose a pseudonymous `subject_code`, never a name. Verify: grep the API responses for any name field — zero hits. (This is the DPDP Act answer.)
- [ ] **[Roxy]** Full synthetic portfolio seeded into Supabase: 8 studies across phases, 12 sites, ~400 subjects, realistic enrolment curves (two studies deliberately lagging target), visits with some overdue, ~30 deviations, ~50 AEs of which 6 are SAEs. Verify: `python -m datagen.seed` populates the DB and the portfolio page reflects it. ⛔ blocks: KPI computation, alerting, signals

### KPIs and alerts

- [ ] **[Kavin]** KPI computation reads from Postgres, not fixtures: enrolment %, screen-failure rate, visit compliance %, open-query ageing, deviation rate per site, days-to-milestone.
- [ ] **[Kavin]** Alert rules engine evaluates and persists three configurable rules: **enrolment lag** (actual < X% of expected-by-date), **ethics/CTRI update due** (approval expiring in < N days), **overdue monitoring visit** (scheduled date passed, no report filed). Verify: change a threshold in config and the alert count on the dashboard changes.
- [ ] **[Kavin]** `/api/alerts` returns severity-ranked alerts with the study they belong to and a deep link.
- [ ] **[Ishan]** Alerts render on the portfolio with severity colour and click through to the offending study. Verify: click an enrolment-lag alert, land on that study's enrolment chart.

### Pharmacovigilance

- [ ] **[Sreeja]** `CodingService` implemented: Sentence Transformers embeds the curated term list into FAISS; free-text AE narrative returns top-3 candidate terms with similarity scores. Verify: `python -m services.pv.cli code "patient had a bad headache"` returns Headache as top hit. Model runs at import on Render's free tier or is precomputed in Colab and shipped as a `.npy` — **decide by hour 8**.
- [ ] **[Sreeja]** The coding interface is documented as a swap point: `MockCodingService` and a `MedDRACodingService` stub implementing the same protocol. Verify: the class docstring says in one sentence why the real dictionary isn't here. This gets read aloud to judges.
- [ ] **[Sreeja]** Reporting timelines computed per NDCT Rules 2019: SAE reported to EC/CDSCO within 24h, narrative within 14 days. Verify: an SAE filed with a past onset date shows as **breached** with hours-remaining negative.
- [ ] **[Sreeja]** `/api/signals` aggregates AEs by coded term × study × severity for the DSMB view. Verify: a term appearing disproportionately in one arm surfaces at the top.
- [ ] **[Ishan]** PV dashboard: AE intake form, coding suggestion picker, timeline countdown clocks, DSMB signal table.

### Everything else

- [ ] **[Kavin]** `STUB_MODE=false` is the deployed default and the click path still passes end to end. ⛔ blocks: hour 15 gate
- [ ] **[Rackshitha]** `docs/compliance-matrix.md` complete — GCP-ASU, ICMR guidelines, NDCT 2019, CTRI, IEC oversight, DPDP 2023 + 2025 Rules, ALCOA+, ISO 27001, CERT-In, e-signatures, informed consent — each mapped to a screen, an endpoint or an explicit deferral. No blank cells.
- [ ] **[Rackshitha]** Q&A prep doc: the 12 questions judges will actually ask, with answers. Lead with "do you have MedDRA?" and "is this real patient data?"

> ### 🚪 GATE — Hour 15: FREEZE
>
> **Pass:** the click path runs on deployed URLs with `STUB_MODE=false`, RBAC returns correct codes for all 7 roles, and the audit chain verifies.
> **Fail branch:** flip `STUB_MODE=true` for the demo and say nothing about it in the pitch. A stub-mode demo that runs beats a real demo that crashes. Fix it in Phase 4 if there's time.

---

# Phase 3 — Freeze and insure · Hours 15–18

**Hard feature freeze. No new features. This phase is not negotiable and cannot be skipped for "just one more thing".**

- [ ] **[Kavin]** Freeze `main`. Feature work moves to branches that will not be merged before hour 18.
- [ ] **[Ishan + Rackshitha]** **Record the backup demo video** against whatever works at this moment. Screen recording, narrated, 4 minutes, uploaded somewhere playable offline. ⛔ blocks: sleeping soundly
- [ ] **[Ishan]** Watch the video back once. If a screen looks broken on camera, that is the only thing anyone fixes before hour 18.
- [ ] **[Avanthika]** Deck locked. Architecture slide, compliance mapping slide, the deferred-scope slide.
- [ ] **[Kavin]** Tag the commit the video was recorded from. If Phase 4 breaks anything, this tag is the demo.
- [ ] **[Caleb]** Rotate any key that got pasted into a chat. Confirm `.env` is not in git: `git log --all --full-history -- '*.env'` returns nothing.
- [ ] **[Everyone]** Two people sleep 90 minutes, staggered. Q&A performance is a function of sleep.

---

# Phase 4 — Depth and polish · Hours 18–22

Only whatever survived. Pick from the top of this list, stop when the clock says so.

- [ ] **[Roxy]** SDTM-shaped **DM** and **AE** domain export as CSV. Verify: `GET /api/export/sdtm?domain=DM` downloads a file whose columns are STUDYID, DOMAIN, USUBJID, SUBJID, SITEID, AGE, SEX, ARM, RFSTDTC.
- [ ] **[Roxy]** Define-XML stub describing those two domains. Verify: it opens in a browser without an XML parse error.
- [ ] **[Roxy]** FHIR R4 resources: `GET /api/fhir/ResearchStudy/{id}` and `/api/fhir/AdverseEvent/{id}` return structurally valid R4 JSON. Verify: paste into any online FHIR validator — resourceType, id, status, and required elements present.
- [ ] **[Sreeja]** Signal detection sharpened: simple disproportionality (observed vs expected per term) rather than raw counts.
- [ ] **[Ishan]** The three screens that appear in the demo get a visual pass. Nothing else gets touched.
- [ ] **[Caleb]** Audit log gets a filter by actor/role/date and an "export audit trail" button for the regulator role.
- [ ] **[Kavin]** E-signature demo: a PI "signs" a milestone, the signature is recorded in the audit chain with intent and timestamp.

---

# Phase 5 — Rehearse · Hours 22–24

- [ ] **[Everyone]** Three clean end-to-end runs on the deployed URL. Not two.
- [ ] **[Kavin]** Warm the Render instance 10 minutes before pitching — free tier cold-starts take ~50 seconds and that is a lifetime on stage.
- [ ] **[Rackshitha]** Q&A drilling: each person answers three hostile questions about someone else's component.
- [ ] **[Ishan]** Confirm the backup video plays offline on the presenting laptop with no network.
- [ ] **[Everyone]** Phones charged, laptop charged, tab layout set, logins already done. Sleep whatever is left.

---

# Cut list — ranked, what dies first

1. **FHIR endpoints** — pure structure demo, one slide covers it if unbuilt.
2. **Define-XML stub** — the SDTM export alone already demonstrates the pattern.
3. **E-signature demo** — the audit trail carries the same credibility.
4. **Disproportionality signal maths** — raw AE counts by term still shows a DSMB view.
5. **SDTM export** — becomes an architecture claim instead of a download.
6. **Semantic coding via FAISS** — falls back to exact-match lookup on the curated CSV. Interface unchanged, so the pitch doesn't change.
7. **Audit log filters and export** — the raw chronological list is enough.
8. **Roles beyond four** — demo as PI, coordinator, PV, regulator. EC, monitor and admin become slides.
9. **Alert rules 2 and 3** — enrolment lag alone proves the alerting concept.

**Never cut:** audit trail, RBAC, the click path, the hour-15 video.

---

# Risk register


| Risk                                                                               | Likelihood | Blast radius                     | Mitigation                                                                                                                                                       | Owner     |
| ---------------------------------------------------------------------------------- | ---------- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| **Late integration** — pieces built separately, first joined at hour 20            | High       | Fatal                            | Contracts frozen at hour 2; stub mode and frontend mocks read the *same* fixture files; `STUB_MODE=false` flipped at hour 12, not hour 22                        | Kavin     |
| **Scope creep from the compliance surface** — 10 regulations feel like 10 features | High       | Severe                           | The compliance matrix is a *document*, not a sprint. Only audit trail, RBAC, pseudonymisation and reporting timelines are built. Everything else is a mapped row | Avanthika |
| **Deploy fails at the end**                                                        | Medium     | Fatal                            | Deploy is live at hour 2 and every push after; hour-15 video is the insurance; tagged commit is the rollback                                                     | Kavin     |
| **Render free tier cold start / sleeps mid-demo**                                  | High       | Moderate                         | Warm it 10 min before; keep the stub-mode Vercel build as instant fallback                                                                                       | Kavin     |
| **Sentence Transformers won't run on free tier RAM**                               | Medium     | Low                              | Decision point at hour 8: precompute embeddings in Colab, ship the `.npy`, ship only the query encoder — or fall back to exact match                             | Sreeja    |
| **RBAC / audit half-done at hour 15**                                              | Medium     | Severe                           | These are Caleb's *only* two tasks. If he's behind at hour 10, Kavin drops KPI work and takes RBAC                                                               | Caleb     |
| **One person's component is the demo's single point of failure**                   | Medium     | Severe                           | Every screen has a fixture-backed path; nothing in the click path requires a live subsystem                                                                      | Ishan     |
| **A judge asks "is this real MedDRA?"**                                            | Certain    | Low *if prepared*, severe if not | Say it first, unprompted, on the PV slide. Owning the limitation reads as rigour; being caught reads as bluffing                                                 | Avanthika |
| **Merge conflicts / lost work**                                                    | Medium     | Moderate                         | One router file per owner; only `main.py` is shared and it's written once at hour 0. Push every 30 minutes                                                       | Kavin     |
| **Someone works 24 hours and is incoherent at Q&A**                                | High       | Moderate                         | Staggered 90-minute sleep in Phase 3. Enforced, not suggested                                                                                                    | Everyone  |


---

# Deferred scope — deliberate staging, read this aloud

Each of these is a conscious decision, not an omission.

- **MedDRA and WHODrug dictionaries** — licensed commercial products; we built a curated term subset behind a `CodingService` interface so the licensed dictionary is a one-class drop-in swap.
- **Live EDC / HIS / ABDM integration** — requires partner systems and credentials that don't exist at a hackathon; we prove interoperability structurally with FHIR R4-conformant resources and a mock endpoint.
- **ISO/IEC 27001 and CERT-In compliant hosting** — a procurement and audit outcome, not a code artifact; addressed in the architecture and deployment design.
- **Full SDTM/ADaM submission package** — we ship SDTM-shaped DM and AE domains plus a Define-XML stub; the pattern generalises, completeness is a data-management exercise measured in weeks.
- **Database-level Row Level Security** — designed and written as SQL policy artifacts; enforcement in this build is at the application layer, where it is testable and demonstrable in the time available.
- **Real informed-consent capture and e-signature PKI** — consent status is modelled and audited; cryptographic signing infrastructure is a production concern.
- **21 CFR Part 11 / full validation documentation** — the audit trail meets the ALCOA+ principles it protects; formal computer system validation is a post-pilot activity.
- **Real patient data** — never, at any stage. The entire portfolio is synthetically generated and the generator is in this repo.

