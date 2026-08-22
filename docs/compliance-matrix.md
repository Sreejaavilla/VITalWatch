# Compliance mapping

Every framework in the problem statement gets a row, and every row gets an answer.
**No blank cells.** *Deferred, and here is why* is a complete answer; a blank is not.

Three honest statuses:

- **Built** — running code you can point at on screen, right now.
- **Modelled** — the data structure and the rules exist and are enforced by the schema or the
  models, but there is no dedicated screen for it.
- **Deferred** — deliberately not built, for a stated reason, with the cost of building it known.

---

## Regulatory — India

| Framework | What it requires | Where it lives | Status |
|---|---|---|---|
| **New Drugs & Clinical Trials Rules 2019**, Third Schedule | SAE reported to the Ethics Committee and licensing authority within **24 hours**; full narrative within **14 days** | `app/pv.py::compute_clocks`, thresholds in `app/config.py`; countdown and breach badges on `/ae` | **Built** |
| **CTRI** | Prospective registration; the registration number recorded against the study; registration *before* first enrolment | `studies.ctri_number`; `/study/{id}` raises a banner when a study is enrolling without one (STU-003 in the seeded data) | **Built** |
| **Institutional Ethics Committee oversight** | Approval on file, expiry tracked, deviations reported to the committee | `studies.ec_expiry_date`; `alerts.ethics_renewal_due` (default 60 days, configurable); `deviations.reported_to_ec` with "Not reported" flagged on the study page | **Built** |
| **GCP-ASU** (Good Clinical Practice for ASU drugs) | Protocol adherence, deviation recording, monitoring visits, source verification | Deviation register per study with category and severity; monitoring visits tracked with an overdue rule; visit compliance as a KPI | **Built** — monitoring visit *reports* are tracked as an attribute, not as documents |
| **ICMR National Ethical Guidelines 2017** | Ethical oversight, informed consent, vulnerable groups | `subjects.consent_version` and `consent_date` are required fields; EC approval and expiry per study | **Modelled** — consent versioning is enforced by the schema; there is no consent screen |
| **DPDP Act 2023** | Data minimisation, pseudonymisation, purpose limitation | `Subject` carries a pseudonymous site code and nothing else — **no name, no date of birth, no resolvable identifier**, enforced by `extra="forbid"` on the model *and* by the absence of the columns | **Built** |
| **Safety signal detection** | Identify terms over-represented in one study for DSMB review | `app/signals.py` — proportional reporting ratio over the coded event set, screening at PRR ≥ 2 with ≥ 3 cases, ranked on `/signals` with the 2×2 contingency shown. Explicitly labelled a hypothesis for a human, not a finding or a causal claim | **Built** |
| **Pharmacovigilance for ASU&H drugs (NPvCC routing)** | Structured AE capture, causality assessment, seriousness, onward reporting | `/ae` intake with WHO-UMC causality, seriousness, outcome; coded terms enable aggregation across sites | **Built** — onward *transmission* to the NPvCC is deferred; no destination endpoint exists to transmit to |

## Data integrity and security

| Framework | What it requires | Where it lives | Status |
|---|---|---|---|
| **ALCOA+** | Attributable, Legible, Contemporaneous, Original, Accurate (+ complete, consistent, enduring, available) | See the ALCOA+ table below | **Built** |
| **Audit trail** | Immutable, time-stamped, before-and-after, attributable | `app/audit.py` — SHA-256 hash chain, `hash = sha256(canonical_json(payload) + prev_hash)`, gapless sequence; `/audit` with a **Verify chain** button that names the first broken row | **Built** |
| **Tamper evidence at the storage layer** | The guarantee must not depend on the application behaving | `BEFORE UPDATE` and `BEFORE DELETE` triggers on `audit_events` raising `RAISE(ABORT, …)` — a direct `UPDATE` from the `sqlite3` shell is rejected | **Built** |
| **Role-based access control** | Distinct views and permissions per role | Not present. The problem statement names seven roles; this build has no authentication and no roles at all | **Deferred** — see the note below |
| **Electronic signatures** | Signed approvals carrying identity, intent and timestamp | Not built. The audit chain is the natural place to anchor one — a signature is an audit event with an intent field and a key | **Deferred** |
| **ISO/IEC 27001** | Information security management system | A certification of an organisation and its processes, awarded after audit. Not a property of source code | **Deferred** — hosting and procurement decision, stated as such on the architecture slide |
| **CERT-In directions** | Log retention, incident reporting timelines, time synchronisation | Log retention is structurally satisfied by an append-only audit trail; the reporting obligations are operational | **Deferred** — same reason |

## Standards and interoperability

| Framework | What it requires | Where it lives | Status |
|---|---|---|---|
| **MedDRA / WHODrug** | Standardised adverse-event and drug coding | `app/terms.csv` — **72 terms we wrote ourselves**, with Ayurveda and Sanskrit synonyms (*jwara*, *atisara*, *kandu*). Every coded result carries `source="curated"` and the UI prints it | **Deferred — licensed.** MedDRA and WHODrug are commercial dictionaries under subscription. We did not have them and did not approximate them. `code()` takes a vocabulary file; a licensed dictionary replaces the file, not the code |
| **CDISC SDTM** | Standardised submission datasets | `app/sdtm.py` — the **`DM` (Demographics) domain** as streamed CSV at `/api/export/sdtm/dm.csv`, with a download on every study page. `AGE` is deliberately absent and `AGEGR1` carries it: we store an age *band*, never an exact age, and submitting `AGEGR1` is the correct expression of that minimisation choice rather than a workaround | **Built — one domain.** A full submission package is dozens of domains plus controlled terminology and a reviewer's guide. One domain proves the mapping, which is the part that was in doubt |
| **CDISC ADaM** | Analysis-ready datasets | Downstream of SDTM; `DM` alone is not enough to derive an analysis dataset from | **Deferred** |
| **Define-XML** | Dataset-level metadata for submission | **Deferred** — follows SDTM |
| **HL7 FHIR R4** | Interoperability with EDC, hospital systems, ABDM | `app/fhir.py` — `ResearchStudy` at `/api/fhir/ResearchStudy/{id}`, with our lifecycle mapped into the FHIR status value set, CTRI as a secondary identifier, and an `HTEST` meta tag so synthetic provenance travels with the resource | **Built — structure only.** Emphatically *not* integration: real interoperability needs a counterparty system and credentials that do not exist at a hackathon. A resource nobody consumes proves the mapping, not the exchange |
| **ABDM** | National health data exchange | **Deferred** — requires sandbox registration and a health-facility identity |

---

## ALCOA+, line by line

This is the one a domain judge will actually push on, so it gets its own table.

| Principle | How this system satisfies it |
|---|---|
| **Attributable** | Every audit row carries an actor. No mutation path writes without one. *Honest limit: the actor is a fixed demo identity, because there is no authentication. With login, this field is the only thing that changes.* |
| **Legible** | Before and after are stored as canonical JSON and rendered readably on `/audit`; nothing is a binary blob or an opaque diff |
| **Contemporaneous** | The timestamp is taken from the server clock at the moment of the write, not supplied by the caller. Application code cannot pass a timestamp; only the seeder can, and only to construct a plausible history |
| **Original** | The audit row is the record, not a copy of one. `UPDATE` and `DELETE` are refused by the database |
| **Accurate** | Statutory deadlines are computed once at intake and stored, because the moment a clock started is itself a regulated fact. Status is derived on read, so it can never go stale |
| **Complete** | The chain is gapless by construction — the verifier checks sequence continuity as well as hashes, so a *deleted* row is as detectable as an *altered* one |
| **Consistent** | Ordering is by sequence number, not by timestamp, so clock skew cannot reorder history |
| **Enduring** | Append-only at the storage layer; the database file is the artefact |
| **Available** | `/audit` for a human, `/api/audit/verify` for a machine, `python -m app.audit --verify` for an inspector at a terminal |

---

## The deferrals, stated plainly

Two of these are worth being able to say out loud without flinching.

**Role-based access control.** The problem statement names seven roles, and this build has
none — no authentication, no authorisation, no enforcement. The reason is a scoping decision:
in the time available, a *presentation-only* role switcher would have looked like access
control while enforcing nothing, and a fake security control is worse than an absent one,
because it invites trust it cannot honour. What exists instead is the thing RBAC is usually
built to support — an audit trail that attributes every change and cannot be edited. Adding
enforcement means adding a session and a permission check at each route; it does not mean
restructuring anything.

**MedDRA.** Say this before you are asked. The terms are ours, the file is in the repository,
and the interface is the part that carries over.
