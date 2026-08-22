# VITalWatch — AIIA CTMS + Pharmacovigilance

**SIH · 24 hours · solo · zero budget · synthetic data only**

One FastAPI process. SQLite. Jinja2 templates. No node, no build step, no external services.

---

# What we are solving

**AIIA runs a portfolio of Ayurveda clinical trials and hosts the National Pharmacovigilance
Coordination Centre for ASU&H drugs. All of it is tracked in disconnected spreadsheets.**

Study status sits in one file, recruitment in another, milestones in a third, adverse events in a
fourth. Nobody can answer "how is the portfolio doing right now?" without days of manual
reconciliation, and by the time the answer arrives it is already stale.

Three things break as a result:

1. **Decisions arrive late.** A study falling behind on enrolment is visible only when someone
  opens the right file and does the arithmetic.
2. **Regulatory deadlines get missed.** A serious adverse event must reach the Ethics Committee
  and the licensing authority within 24 hours under the New Drugs and Clinical Trials Rules 2019.
   A spreadsheet does not start a clock and does not chase anyone.
3. **There is no audit trail.** A cell can be changed by anyone, at any time, with no record of who
  changed it or what it said before. ALCOA+ data integrity is not achievable in a file that can be
   silently edited.

Underneath all three: **no single, real-time, auditable view of the study lifecycle.**

# How we solve it

One application covering protocol → EC approval → CTRI registration → site activation → screening
→ enrolment against target → visit and deviation compliance → milestones → close-out, with
pharmacovigilance attached, because AIIA hosts the NPvCC and safety reporting is not a separate
concern from trial management.


| The problem                        | The mechanism                                                                                    |
| ---------------------------------- | ------------------------------------------------------------------------------------------------ |
| Status is scattered and stale      | One SQLite schema, one process; every page computes from the same source                         |
| Nobody notices a study slipping    | Alert rules on configurable thresholds — enrolment lag, EC renewal due, monitoring visit overdue |
| Statutory clocks are not tracked   | AE intake starts a 24-hour and 14-day clock and shows breach status                              |
| Free-text AEs cannot be aggregated | Coding to a curated term set, then aggregation by term for the DSMB view                         |
| Records can be changed invisibly   | Append-only hash-chained audit trail where tampering is detectable and locatable                 |


**The audit trail is the pitch.** Everything else a disciplined spreadsheet could imitate; an
immutable chain is something it structurally cannot provide. Build that first and well.

## Architecture — deliberately boring

one python process
  ├─ FastAPI          API routes + server-rendered pages, same app
  ├─ Jinja2           HTML templates, no build step
  ├─ SQLite (stdlib)  one file, seeded at startup
  └─ Tailwind + Chart.js from CDN

**Why not a separate frontend?** A second deploy is a second thing that can be down, a CORS
config that will bite once, and a build step between you and a working page. Solo in 24 hours,
every boundary you remove is time back.

**Why SQLite?** No account, no connection string, no service to be down at hour 20. Still real SQL,
real constraints, and a real append-only trigger on the audit table — which is what you demo.

**Say this to judges, don't hide it:** synthetic data in an embedded database, data access behind
one module, Postgres is a config change. That reads as engineering judgment, not a shortcut.

# Repo layout

VITalWatch/
├─ app/
│  ├─ main.py          FastAPI app, API routes and page routes
│  ├─ config.py        settings, alert thresholds
│  ├─ models.py        pydantic models — one file, the data model
│  ├─ db.py            sqlite3 connection, schema, startup seed
│  ├─ audit.py         hash-chained append-only trail + verifier
│  ├─ kpi.py           KPI computation
│  ├─ alerts.py        alert rules
│  ├─ pv.py            AE intake, coding, NDCT-2019 reporting clocks
│  ├─ datagen.py       synthetic portfolio generator
│  ├─ terms.csv        curated AE term subset (stands in for MedDRA)
│  ├─ templates/       base · portfolio · study · ae · audit
│  └─ static/          app.css
├─ data/ctms.db        generated, gitignored
├─ docs/               deck outline, compliance matrix, demo script, Q&A prep
├─ scripts/            run.sh, seed.sh, verify_audit.sh
└─ ROADMAP.md · README.md · requirements.txt · .env.example

Everything under `app/` is one importable package. Every module runs standalone —
`python -m app.datagen`, `python -m app.pv "severe headache"`, `python -m app.audit --verify`.

---



## The one thing that matters

**At hour 6 there is a demo.** Everything after that is improvement, not survival.
**At hour 13 there is a hard freeze and a recorded video.** Non-negotiable.
Anything not working by hour 13 is cut, not finished.

Solo means the deck, the demo script and the Q&A prep are also yours. They are in Phase 3, not
bolted on at hour 23.

---



# Phase 0 — Skeleton · Hours 0–2

Collapse the multi-service scaffold into one app and get a page rendering.

- [x] Move the 12 models from `contracts/models/*.py` into a single `app/models.py`. They are
  already written and tested — this is a merge, not a rewrite. Verify: `python -c "import app.models"` exits 0.
- [x] Delete `frontend/`, `backend/`, `contracts/`, `services/`, `datagen/`, `render.yaml`,
  `.python-version`. One app now. ⛔ blocks: everything
  *(Source removed. Untracked build artefacts survive —* `frontend/node_modules` *and*
  `frontend/.next` *at 365 MB, plus* `__pycache__` *— so* `rm -rf frontend backend contracts datagen` *is still worth running once.)*
- [x] `app/db.py`: `sqlite3` schema for studies, sites, subjects, visits, deviations, queries,
  adverse_events, milestones, alerts, audit_events. Verify: `python -m app.db --init` creates
  `data/ctms.db` and `.tables` lists 10 tables.
- [x] `app/db.py` seeds from `app/datagen.py` on startup if the DB is empty. Verify: delete
  `data/ctms.db`, start the app, the portfolio page has data.
- [x] `app/main.py`: FastAPI with Jinja2 templates mounted, `/health` returns 200, `/` renders
  `base.html` with the app title. Verify: `uvicorn app.main:app` then open localhost:8000.
- [x] `app/templates/base.html`: Tailwind CDN, nav to the four screens, "synthetic data" footer.

> ### 🚪 GATE — Hour 2
>
> **Pass:** `uvicorn app.main:app` serves a styled page and `data/ctms.db` has seeded tables.
> **Fail branch:** drop Jinja2, return JSON from FastAPI, and build the UI at Phase 1 instead.
> A working data layer with no UI beats a pretty page with no data.

---



# Phase 1 — Walking skeleton · Hours 2–6

Every screen reachable with real data from SQLite. **This is a demo by hour 6.**

- [x] `/portfolio` — six KPI tiles (active studies, enrolled vs target, sites activated, open
  queries, overdue monitoring visits, open SAEs) plus a study table. Verify: numbers change
  when you edit a row in SQLite directly.
- [x] `/study/{id}` — enrolment vs target, site list, milestone timeline, deviation and query
  counts. Verify: clicking a study row from the portfolio lands here with the right data.
- [x] `/ae` — AE list plus an intake form that POSTs and redirects back with the new row visible.
- [x] `/audit` — chronological table: actor, action, resource, before/after, UTC timestamp.
- [x] Every mutating route writes an audit row. Verify: file an AE, see that exact event on
  `/audit` with `after` populated. ⛔ blocks: Phase 2 audit work
- [x] Nav links between all four screens work. No dead ends, no 404s.

> ### 🚪 GATE — Hour 6: WALKING SKELETON
>
> **Pass:** portfolio → study drill-down → file an AE → see it in the audit log, no crash.
> **Fail branch:** stop everything else until this path completes. A working skeleton at hour 8
> and nothing else is still a demo. Four half-built features at hour 13 is not.

---



# Phase 2 — Substance · Hours 6–13

The parts judges probe.

### Audit trail — do this first, it is the pitch

- [x] Hash chain: each row stores `prev_hash` and `sha256(canonical_json(payload) + prev_hash)`.
- [x] `python -m app.audit --verify` walks the chain and prints OK, or the sequence number of the
  first tampered row. Verify: `UPDATE audit_events SET after='...' WHERE seq=3`, re-run,
  it prints 3. ⛔ blocks: the strongest 30 seconds of the demo
- [x] SQLite trigger raising on UPDATE or DELETE of `audit_events`, so the guarantee does not
  depend on application code. Verify: the UPDATE above fails at the DB level.
- [x] `/audit` gets a **Verify chain** button calling the verifier and showing the result.



### Pharmacovigilance

- [x] `app/pv.py` codes a free-text narrative against `terms.csv` (normalise, exact, then
  `difflib` fuzzy). Verify: `python -m app.pv "patient had a bad headache"` returns Headache.
- [x] Coding results carry a `source` field reading `"curated"` — never implies MedDRA.
- [x] NDCT Rules 2019 clocks: SAE → EC/licensing authority within 24h, narrative within 14d,
  computed from the server clock on intake. Verify: an SAE with a past onset shows BREACHED
  with negative hours remaining.
- [x] AE intake form shows coding suggestions and the countdown after submit.



### KPIs and alerts

- [x] KPI computation reads SQLite: enrolment %, screen-failure rate, visit compliance,
  open-query ageing, deviation rate, days to next milestone.
- [x] Three alert rules from `config.py` thresholds: enrolment lag, EC renewal due, monitoring
  visit overdue. Verify: change `ALERT_ENROLMENT_LAG_PCT`, restart, the alert count changes.
- [x] Alerts render on `/portfolio` severity-ranked, each linking to its study.



### Data

- [x] `app/datagen.py` produces a portfolio that tells a story: 8 studies, 12 sites, ~400
  subjects, **two studies deliberately behind target**, **one EC approval expiring in under
  30 days**, **three overdue monitoring visits**, ~50 AEs of which 6 are serious, **one AE
  term over-represented in one study**. Verify: every alert type has something to fire on and
  the DSMB view has a visible signal.
- [x] Fixed seed. Verify: regenerating twice produces identical numbers. The demo, the deck and
  the video must agree.

> ### 🚪 GATE — Hour 13: FREEZE
>
> **Pass:** the click path runs, the chain verifies, an SAE shows a live countdown.
> **Fail branch:** demo whatever works and say nothing about the rest. Fix it in Phase 4 if there
> is time.

---



# Phase 3 — Freeze and insure · Hours 13–16

**Hard feature freeze. This phase cannot be skipped for "just one more thing."**

- [ ] Commit and tag. Feature work goes on a branch that will not merge before hour 16.
  *(Left for you — nothing has been committed or pushed on your instruction. The tree is clean
  and the freeze point is reproducible from the fixed seed regardless.)*
- [ ] **Record the backup demo video** against whatever works right now. Narrated, 4 minutes,
  playable offline. ⛔ blocks: sleeping
  *(Yours.* `docs/demo-script.md` *is the script — record straight down it.)*
- [ ] Watch it back once. If a screen looks broken on camera, that is the only thing you fix.
- [x] `docs/demo-script.md` — the exact click path, in order, with what you say on each screen.
  *(Seven beats, timed to 4:40 with the two cuts named. Every number, coded term and confidence
  in it was run against the live app, not written from memory.)*
- [x] `docs/compliance-matrix.md` — every framework as a row: GCP-ASU, ICMR guidelines, NDCT 2019,
  CTRI, IEC oversight, DPDP 2023, ALCOA+, ISO 27001, CERT-In, CDISC, FHIR, MedDRA. Each maps
  to a screen, a module, or an explicit deferral. **No blank cells.**
  *(20 rows across three tables, statuses Built / Modelled / Deferred, plus a nine-line ALCOA+
  table of its own. Every code reference in it verified against the schema.)*
- [x] `docs/qa-prep.md` — 12 questions with answers. Lead with "is that real MedDRA?" and "is this
  real patient data?"
  *(Plus three questions I would struggle with, written down so they are not discovered on stage —
  the largest is that seeded history is not audited, only live mutations are.)*
- [x] Deck locked: problem, architecture, live demo, audit trail, pharmacovigilance, compliance
  matrix, deferred scope.
  *(Nine slides speced in* `docs/deck-outline.md`*, with what stays off the deck.* `docs/architecture.md`
  *rewritten to the one-process build with a diagram and the three swap points. Building the actual
  slides is yours.)*
- [x] Sleep 90 minutes. Q&A performance is a function of sleep and you have no teammate to cover.

---



# Phase 4 — Depth · Hours 16–21

Only what survives. Top of the list first, stop when the clock says so.

- [ ] ~~**"View as" role selector**~~ — **cut, on your standing "no roles" instruction.**
  `docs/qa-prep.md` Q4 answers the seven-roles question directly instead: a presentation-only
  switcher would look like access control while enforcing nothing, and a fake security control is
  worse than an absent one. Building it now would contradict the answer we give on stage.
- [x] DSMB signal view: AE counts by coded term × study × severity, ranked.
  *(`app/signals.py` + `/signals`. Proportional reporting ratio with the 2×2 contingency shown,
  screening at PRR ≥ 2 with ≥ 3 cases. The page deliberately shows sub-threshold rows — the
  Arthralgia row scores 14 on two cases and is correctly not flagged, which is the demo's best
  domain moment. A panel states what disproportionality does not claim.)*
- [x] SDTM-shaped DM export as CSV. Columns: STUDYID DOMAIN USUBJID SUBJID SITEID AGE SEX ARM RFSTDTC.
  *(`app/sdtm.py`, streamed at `/api/export/sdtm/dm.csv`, download button on every study page.
  **`AGE` is deliberately not a column** — we hold an age band, never an exact age, so the domain
  carries `AGEGR1`. That is the DPDP minimisation choice expressed correctly, not missing data.)*
- [x] Audit log filters by actor and date range.
  *(Filtering narrows the display only — verification always walks the whole chain. A green
  banner over a narrowed selection would be the most misleading thing on the screen.)*
- [ ] Deploy to one host — a single Render web service, or run locally and expose with a tunnel.
  One service, one URL. Verify: `/health` responds on the public URL and you have warmed it.
  *(Prepared, not done — it needs your account. `render.yaml` defines the one service and
  `./scripts/deploy_check.sh <url>` checks all 13 endpoints against it and warms a cold start.
  Ephemeral disk is fine here: the fixed seed means a restart rebuilds an identical portfolio.)*
- [x] Visual pass on the three screens that appear in the demo. Nothing else gets touched.
  *(All six pages rendered and swept for unrendered template syntax, `None` leaking into text and
  empty states. Added the missing cross-links: study → FHIR and SDTM export, AE → signals.)*
- [x] FHIR R4 `ResearchStudy` JSON at `/api/fhir/ResearchStudy/{id}`. Structure only.
  *(`app/fhir.py`. Our lifecycle collapses into the FHIR status value set rather than inventing
  codes outside it, CTRI rides as a secondary identifier, and an `HTEST` meta tag keeps synthetic
  provenance attached to the resource if it ever leaves the system.)*

---



# Phase 5 — Rehearse · Hours 21–24

- [x] Three clean end-to-end runs. Not two.
  *(`scripts/rehearse.py` — reseeds and walks the whole script three times, asserting all 45
  claims the demo makes out loud. It caught its own first drift: filing the beat-3 AE moves the
  Arthralgia ratio from 14.0 to 14.33, so the script now says "over 14".)*
- [ ] Time the demo. Four minutes means four minutes.
  *(Yours — needs a stopwatch and your voice. The script totals 5:05 with the cuts already
  ranked, and `docs/cue-card.md` is the one-page version for the podium.)*
- [ ] Answer all 12 Q&A questions out loud, standing up. *(13 now — `docs/qa-prep.md`.)*
- [ ] Confirm the backup video plays offline on the presenting laptop.
- [ ] Tabs, zoom, notifications off, laptop charged, app already running and warmed.
  *(`./scripts/deploy_check.sh` warms every page; the pre-flight list is at the top of
  `docs/demo-script.md` and on the cue card.)*
- [ ] Sleep whatever is left.

---



# Cut list — ranked, what dies first

1. **FHIR endpoint** — one slide covers it if unbuilt.
2. **SDTM export** — becomes an architecture claim instead of a download.
3. **Audit log filters** — the raw chronological list is enough.
4. **"View as" role selector** — falls back to a roles slide.
5. **DSMB signal view** — the AE list alone shows pharmacovigilance working.
6. **Alert rules 2 and 3** — enrolment lag alone proves the concept.
7. **Deployment** — demo from localhost. "Cloud-based" becomes an architecture claim; every
  judge has seen a laptop demo.
8. **Fuzzy coding** — exact match only. The interface and the pitch do not change.

**Never cut:** the audit trail, the click path, the hour-13 video.

---



# Risk register


| Risk                                                                         | Likelihood | Blast radius      | Mitigation                                                                           |
| ---------------------------------------------------------------------------- | ---------- | ----------------- | ------------------------------------------------------------------------------------ |
| **Solo scope creep** — no one to say "that's not in scope"                   | High       | Fatal             | The cut list is the contract with yourself. Reread it at every gate                  |
| **Feature freeze slips** — "just one more thing" at hour 14                  | High       | Fatal             | The video is recorded at hour 13 against whatever works. Tag the commit              |
| **Nothing demoable at hour 13**                                              | Medium     | Fatal             | Hour-6 gate is the early warning. If it slips past hour 8, start cutting immediately |
| **Audit chain half-done**                                                    | Medium     | Severe            | It is the first Phase 2 task, before KPIs, before PV. Do it while fresh              |
| **Synthetic data has no story** — alerts fire on nothing, DSMB view is empty | Medium     | Moderate          | The datagen task lists the exact anomalies to plant. Verify each one fires           |
| **Exhaustion at Q&A**                                                        | High       | Severe            | 90 minutes in Phase 3, enforced. No teammate can cover for you                       |
| **A judge asks "is that real MedDRA?"**                                      | Certain    | Low *if prepared* | Say it first, unprompted, on the PV slide                                            |
| **Demo machine fails on stage**                                              | Low        | Fatal             | The hour-13 video, offline, on the presenting laptop                                 |


---



# Deferred scope — deliberate staging, read this aloud

Each of these is a decision, not an omission.

- **MedDRA and WHODrug** — licensed commercial dictionaries. We built a curated term subset behind
one coding function, so a licensed dictionary is a drop-in swap.
- **Live EDC / HIS / ABDM integration** — requires partner systems and credentials that do not
exist at a hackathon. Interoperability is shown structurally with FHIR R4-shaped resources.
- **PostgreSQL and multi-user deployment** — SQLite with data access behind one module; the swap
is a config change. Correct for a single-node demo, explicitly not the production posture.
- **Enforced role-based access control** — seven roles are modelled and presented; authentication
and server-side enforcement are the first thing built after the hackathon.
- **ISO/IEC 27001 and CERT-In hosting** — a procurement and audit outcome, not a code artifact.
- **Full SDTM/ADaM submission package** — one domain demonstrates the pattern; completeness is a
data-management exercise measured in weeks.
- **Electronic signature PKI and 21 CFR Part 11 validation** — the audit trail meets the ALCOA+
principles; formal computer system validation is a post-pilot activity.
- **Real patient data** — never, at any stage. The entire portfolio is synthetic and the generator
ships in this repo.

