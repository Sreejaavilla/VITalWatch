# Architecture — OWNER: Rackshitha (narrative) / Kavin (facts)

One slide's worth. Cover:

* Next.js on Vercel → FastAPI on Render → Supabase Postgres, JWT between them
* Where the audit chain sits and why direct DB edits are detectable
* RBAC resolved from a declarative matrix, not scattered through route handlers
* Stub mode as an architectural property, not a hack
* Hosting posture: ISO 27001 / CERT-In as **deployment design**, not code — say this plainly
* Where a real MedDRA, a real EDC and real RLS each plug in, and what changes when they do (very little — that's the point)
