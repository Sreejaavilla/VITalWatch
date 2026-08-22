# Q&A defence — OWNER: Avanthika

Every person must be able to answer three questions about someone else's component.

## Answer these before being asked

1. **"Is that real MedDRA?"** — No, and say it first, on the slide, unprompted. Licensed
   dictionary; we built a curated subset behind an interface so it's a one-class swap.
2. **"Is this real patient data?"** — Never. Fully synthetic, generator is in the repo,
   fixed seed. `subjects` has no name column at the schema level.
3. **"What stops an admin editing the database directly?"** — Hash-chained audit trail;
   `verify` detects it and names the row. Append-only enforced by a DB trigger, not just
   app code. Offer to demonstrate it live.
4. **"Is it actually integrated with an EDC / ABDM?"** — No. FHIR R4 conformant structure,
   mock endpoint. Real integration needs partner credentials. Deliberately staged.
5. **"How is this different from a spreadsheet?"** — Real-time computed KPIs, configurable
   alerting, enforced role separation, and an audit trail a spreadsheet structurally cannot have.
6. **"How does RBAC actually work?"** — Declarative matrix in `roles.yaml`, one dependency,
   default deny. Show the coordinator-gets-403-on-export test.
7. **"Would this pass an inspection?"** — ALCOA+ principles are implemented; formal computer
   system validation is a post-pilot activity, and we're explicit about that.
8. **"How long to production?"** — Name the deferred list and what each one costs. Staged
   delivery, not missing features.
9. **"Why Ayurveda-specific?"** — GCP-ASU, ASU&H pharmacovigilance routing to the NPvCC,
   CTRI registration, formulation coding.
10. **"What happens if the internet dies?"** — Stub mode. Show it.
11. **"Who built what?"** — Six people, six components, name them. Judges reward clear ownership.
12. **"What would you do with another week?"** — Real RLS, more SDTM domains, live FHIR
    against a test EDC, e-signature PKI. In that order.
