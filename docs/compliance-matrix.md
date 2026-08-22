# Compliance mapping — OWNER: Avanthika

Every row gets an answer before hour 15. **No blank cells.** "Deferred, and here's why"
is a complete answer; a blank is not.

| Framework | Requirement | Where addressed | Built / Designed / Deferred |
|---|---|---|---|
| GCP-ASU | Good Clinical Practice for ASU drugs | | |
| ICMR National Ethical Guidelines | Ethical oversight, consent, vulnerable groups | | |
| New Drugs & Clinical Trials Rules 2019 | SAE reporting: 24h notification, 14d narrative | `services/pv/timelines/` | Built |
| CTRI | Prospective registration, registration number on study | | |
| Institutional Ethics Committee | Approval, expiry tracking, deviation reporting | | |
| DPDP Act 2023 + 2025 Rules | Data minimisation, pseudonymisation, purpose limitation | `subjects` has no name column | Built |
| ALCOA+ | Attributable, legible, contemporaneous, original, accurate | `backend/app/audit/chain.py` | Built |
| Audit trail | Immutable, time-stamped, before/after | Hash-chained, append-only | Built |
| Role-based access | 7 distinct roles incl. read-only regulator | `contracts/roles.yaml` + `auth/rbac.py` | Built |
| CDISC SDTM/ADaM | Standardised submission datasets | DM + AE domains only | Partial — deferred, see ROADMAP |
| Define-XML | Dataset metadata | Stub, 2 domains | Partial |
| HL7 FHIR R4 | Interoperability with EDC / HIS / ABDM | Conformant resource shapes, mock endpoint | Designed |
| MedDRA / WHODrug | Standard AE and drug coding | Curated subset behind a swap-in interface | Deferred — licensed |
| ISO/IEC 27001 | Information security management | Architecture slide | Designed |
| CERT-In | Hosting and incident reporting norms | Architecture slide | Designed |
| Electronic signatures | Signed approvals with intent and timestamp | Audit-chain signature event | Phase 4 |
| Informed consent | Version, date, re-consent tracking | `Subject.consent_version` | Built (modelled) |
