# Architecture

One process. One SQLite file. No build step, no second service, no node, no network dependency
beyond two CDN links for styling.

That is a deliberate choice for a 24-hour solo build, and the justification is operational rather
than aesthetic: **the whole system recovers from total data loss in about two seconds**
(`rm data/ctms.db` and restart), and it regenerates identically because the seed is fixed. A demo
you can destroy and rebuild on stage is a demo you can give honestly.

```
                     browser
                        │
                 HTML over HTTP
                        │
        ┌───────────────▼───────────────┐
        │   FastAPI  ·  one process     │
        │                               │
        │   main.py    routes, pages    │
        │   db.py      sqlite | postgres │
        │   kpi.py     computed metrics │
        │   roles.py   per-role lenses  │
        │   alerts.py  threshold rules  │
        │   pv.py      coding + clocks  │
        │   audit.py   hash chain       │
        │   models.py  pydantic schema  │
        └───────────────┬───────────────┘
                        │  DATABASE_URL selects one
             ┌──────────┴──────────┐
             ▼                     ▼
   ┌───────────────────┐  ┌───────────────────┐
   │ Supabase Postgres │  │  data/ctms.db     │  append-only guard
   │ 11 tables · RLS   │  │  SQLite fallback  │  on audit_events,
   └───────────────────┘  └───────────────────┘  enforced on both
                        ▲
              app/datagen.py  ·  fixed seed 20260822
              app/terms.csv   ·  72 curated terms
```

**Rendering.** Jinja2 templates rendered server-side, Tailwind and Chart.js from a CDN. No
client build, so there is no state where the frontend and backend disagree about a schema.

**Data access.** Every query goes through `db.py`, which yields a per-request connection with
foreign keys enforced. There is no ORM: the schema is ordinary SQL that a reviewer can read.

## Where the audit chain sits

Not in a middleware, and not as a decorator. `audit.record()` is called explicitly by each
mutating handler, **inside the same transaction as the change it describes** — the write and its
audit row commit together or neither does. This is verified, not assumed: forcing `record()` to
raise during an AE submission leaves no adverse-event row behind.

The guarantee has two layers, and the second is the one that matters:

1. **Application layer** — hash chain. Each row stores `sha256(canonical_json(payload) + prev_hash)`
   and a gapless sequence number, so both alteration *and* deletion are detectable.
2. **Storage layer** — `BEFORE UPDATE` and `BEFORE DELETE` triggers on `audit_events` that
   `RAISE(ABORT, …)`. A direct `UPDATE` from the `sqlite3` shell is rejected outright, so the
   guarantee does not depend on the application being uncompromised.

## The three swap points

Say these on the slide. Each is a boundary chosen so that production readiness is a substitution
rather than a rewrite. **One of the three has since been taken**, which is the useful thing to
say about it: the boundary held, and the swap cost a driver rather than a rewrite.

| Boundary | Today | Production | What changes |
|---|---|---|---|
| **Vocabulary** | `app/terms.csv`, 72 curated terms | MedDRA / WHODrug under licence | The file. `code()` is unchanged — it takes a vocabulary and returns a term, a code and a confidence |
| **Storage** | ~~SQLite, one file~~ **Supabase Postgres** | Postgres with a private network and backups | **Done.** `DATABASE_URL` selects the engine; SQLite remains as the offline fallback. Both run the same queries and produce the same audit head hash |
| **Identity** | one fixed demo actor | authenticated session | The `actor` argument at each `audit.record()` call site. Every mutation already flows through one audited path, so there is exactly one field to populate |

## Configuration

Every number a judge might ask "is that hardcoded?" about is in `app/config.py`, read from the
environment, documented in `.env.example`: alert thresholds, statutory clock durations, the
generator seed. `ENROLMENT_LAG_PCT=95 python -m app.alerts` moves the alert count from 8 to 10;
`MONITORING_OVERDUE_DAYS=120` drops it to 5.

## Hosting posture

ISO/IEC 27001 and the CERT-In directions are **deployment and procurement outcomes, not code
artefacts** — a certification of an organisation and its processes, awarded after audit. Say this
plainly rather than implying the repository satisfies them. What the code contributes is the part
that would otherwise be hardest to evidence at audit: an append-only, time-ordered, tamper-evident
log with before-and-after state on every entry.
