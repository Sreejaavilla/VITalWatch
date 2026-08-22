# Q&A preparation

Answer these standing up, out loud, before the pitch. Reading them is not the same as saying
them. The first two get answered on a slide **before anyone asks**, because volunteering a
limitation reads as confidence and conceding one under questioning reads as a miss.

Two rules for the whole session:

1. **Lead with the answer, then the reason.** "No, and here's why" — not a paragraph that
   arrives at "no".
2. **Never bluff a number.** "I don't know, here's how I'd find out" costs you nothing.
   A wrong number that a domain judge catches costs you the room.

---

### 1. "Is that real MedDRA?"

**No — and I say so on the slide before you ask.** MedDRA and WHODrug are licensed commercial
dictionaries under subscription; we don't have them and I'm not going to imply otherwise. What
you're seeing is 72 terms I wrote for this demo, in `app/terms.csv`, including Ayurveda and
Sanskrit synonyms that MedDRA itself doesn't carry — *jwara*, *atisara*, *kandu*. Every coded
result carries `source="curated"` and the interface prints it, so nothing downstream can quietly
imply it's the real dictionary.

The part that matters is the interface. `code()` takes a vocabulary file and returns a term, a
code and a confidence. A licensed dictionary replaces the file. It does not change the code.

### 2. "Is this real patient data?"

**No. There has never been real data in this system and it can't hold any.** Every record is
synthetic, from a seeded generator that's in the repository — `app/datagen.py`, fixed seed, so
it regenerates identically.

That's the weak version of the answer. The strong one: a `Subject` in this system has no name
field, no date of birth, and no resolvable identifier. Not "we left them blank" — the columns
don't exist, and the model rejects extra fields, so an attempt to attach a name raises rather
than silently storing it. Data minimisation under DPDP 2023 is enforced by the schema, not by
a policy someone has to remember.

### 3. "What stops an administrator editing the database directly?"

**Nothing stops them. Everything detects them — and I'll show you.**

Each audit row stores the SHA-256 of its own contents plus the hash of the row before it. Alter
any row and every subsequent hash stops matching. The **Verify chain** button doesn't just say
something is wrong; it names the sequence number of the first altered row.

And the first line of defence isn't the application at all: `UPDATE` and `DELETE` on
`audit_events` are refused by database triggers, so compromising the app doesn't get you there.
*(Offer the live demo. It takes 40 seconds and it's the strongest thing in the pitch.)*

### 4. "Where's the role-based access control? The problem statement names seven roles."

**It isn't there, and that was a decision rather than an oversight.** In 24 hours solo I could
have built a role *switcher* — a dropdown changing what the dashboard shows, enforcing nothing.
That looks like access control on stage. I'd rather show you no security control than a fake
one, because a fake one invites exactly the trust it can't honour.

What I built instead is the thing RBAC usually exists to support: an audit trail that attributes
every change and can't be edited. Adding real enforcement is a session and a permission check
per route — roughly a day, and it doesn't restructure anything, because every mutation already
flows through one audited path.

### 5. "How is this different from a spreadsheet?"

Four things a spreadsheet structurally cannot do. KPIs computed from the underlying records, so
they can't disagree with them. Alert thresholds that live in configuration and re-evaluate on
every read. Statutory deadlines that start themselves and keep counting. And an audit trail that
detects its own modification — a spreadsheet's change history is a feature of the spreadsheet,
which means whoever owns the file owns the history.

The honest comparison: a spreadsheet is fine at holding this data. It fails the moment someone
has to *prove* it wasn't altered.

### 6. "Would this pass a regulatory inspection?"

**Not today, and no 24-hour build would.** What's implemented is the ALCOA+ principle set —
I can walk you through attributable, contemporaneous and original one by one against the code.

What's missing is not features, it's process: formal computer system validation, an IQ/OQ/PQ
package, SOPs, a validation master plan. That's months of documented testing against written
requirements, and it's the correct next phase for a system like this — not something you retrofit
after go-live.

### 7. "Your alert thresholds — are those hardcoded?"

No. They're in `app/config.py`, read from the environment, documented in `.env.example`. Change
`ENROLMENT_LAG_PCT` from 80 to 95 and the alert count moves from 8 to 10; drop
`MONITORING_OVERDUE_DAYS` from 14 to 120 and it falls to 5. Those are shell commands, and I can
run them now.

The one worth explaining: enrolment lag is measured against **plan-to-date**, not against the
final target. A study four months into a two-year recruitment window at 20% of target is on
schedule; the same number at month twenty is a study in trouble. Comparing to the final target
would flag every young study and bury the real ones.

### 8. "Is it integrated with an EDC, a hospital system, or ABDM?"

**No.** Real integration needs a partner system, credentials and a sandbox registration, none of
which exist at a hackathon — and a mock endpoint I built and called myself proves the shape of a
message, not interoperability. I'd rather name that gap than dress it up. The two FHIR R4
resources this data maps onto are `ResearchStudy` and `ResearchSubject`, and mapping is where
that work starts.

### 9. "Why does this need to be Ayurveda-specific? Why not a generic CTMS?"

Four things a generic CTMS gets wrong. Pharmacovigilance for ASU&H drugs routes to the **NPvCC**,
a separate national channel from the modern-medicine PvPI pathway. **GCP-ASU** is its own
guideline set, not ICH-GCP with a find-and-replace. Adverse events arrive described in
classical terminology — *kandu*, *jwara*, *atisara* — and coding that ignores it drops signal on
the floor, which is why those synonyms are in my vocabulary file. And formulations are
polyherbal preparations, not single molecules, so "the drug" is a compound entity.

### 9b. "Your signal detection — is that a real method or did you invent it?"

PRR, the proportional reporting ratio: the term's share of one study's events divided by its
share everywhere else, screened at **PRR ≥ 2 with at least 3 cases**. That's the conventional
first-pass screen, and the 2×2 table it comes from is on the page.

The case minimum is the part worth defending. There's a row on that screen with a PRR of 14 that
is deliberately *not* flagged, because it has two cases — at that count the ratio is arithmetic
rather than evidence. And I'd rather state the limits than oversell it: disproportionality is not
an incidence rate, because the denominator is other reports rather than patients exposed, and it
is not causation. It produces a triage order for a DSMB. Real practice would add a confidence
interval; at these volumes that would be noise, so I report the case count plainly instead.

### 10. "What happens if this falls over during the demo?"

Deleting the database and restarting rebuilds the entire portfolio in about two seconds, and the
seed is fixed, so every number comes back identical — the demo, the deck and the video can't
disagree with each other. And there's a recorded run on this laptop that plays offline.

### 11. "SQLite? For a multi-site clinical trial system?"

Correct for one node and one demo; wrong for production, and I'll say that unprompted. Every
query goes through one module, the schema is ordinary SQL, and the migration to Postgres is a
connection change plus the constraints Postgres would enforce more strictly than SQLite does.

What SQLite bought me: the whole system is one process with no infrastructure, which is why the
recovery answer to question 10 is two seconds rather than "let me redeploy".

### 12. "What would you do with another week?"

In order. **Authentication and enforced roles** — it's the largest gap and everything else
depends on knowing who is acting. **More SDTM domains** — `DM` is exported today, and `AE` is the
obvious next one because the events are already coded. **Postgres and a hardened deployment.**
**A live FHIR exchange against a test EDC** — the resource shapes exist, the counterparty doesn't.
Then a confidence interval on the PRR, once there's enough volume for one to mean anything.

Notably not on that list: more dashboard screens. The gap isn't surface area.

---

## Questions I'd struggle with — think about these before the room does

- **"Show me the audit entry for a subject being enrolled."** Enrolment happens in the seeder,
  so the audit trail covers AE intake and study lifecycle events, not every table.
  Honest answer: every *mutation the running application performs* is audited; seeded history
  isn't a user action. Don't overclaim "every change is audited" without that qualifier.
- **"What's the false-positive rate on your coding?"** I don't have a measured number — there's
  no annotated corpus to measure against. I can describe the failure modes I found and fixed:
  short synonyms fuzzy-matching unrelated words, which is why fuzzy matching has a minimum
  length. Give the mechanism, not a number I can't defend.
- **"Who else worked on this?"** Solo build. Say it plainly — it reframes the scope rather
  than shrinking it.
