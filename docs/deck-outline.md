# Deck — locked at hour 15

Nine slides. The demo is slide 4 and it is four minutes of the total; everything else is
support. **If a slide does not survive being read in ten seconds, it is too dense.**

Rule for the whole deck: no slide claims anything the demo cannot show or the repository
cannot back. The deferred slide is not an apology, it is evidence of judgement.

---

### 1 · The problem
AIIA runs the National Pharmacovigilance Coordination Centre for ASU&H drugs and a portfolio of
clinical trials at the same time. That portfolio lives in disconnected spreadsheets and email.
Two consequences, and only these two on the slide:

- Nobody can see the whole portfolio at once, so recruitment slippage is found late.
- Statutory deadlines have no clock attached to them — the **24-hour SAE window** under the
  New Drugs and Clinical Trials Rules 2019 depends on someone remembering it.

### 2 · What this is
One auditable view of the trial lifecycle: portfolio → study → adverse event → audit trail.
Configurable alerts, statutory clocks that run themselves, and a log that can prove it hasn't
been altered.

One line, in the same size as everything else: **synthetic data throughout, no real
participant record at any stage.**

### 3 · Architecture
The diagram from `architecture.md`. Say the shape out loud — *one process, one file, no build
step* — and say why: a system that recovers from total failure in two seconds is a system you
can demo honestly.

Mark the three swap points on the diagram itself: vocabulary file → licensed dictionary,
SQLite → Postgres, demo actor → authenticated session.

### 4 · Live demo · 4 minutes
Per `demo-script.md`. **Do not narrate the architecture again while demoing.**

### 5 · The audit trail
The slide that earns the marks. Three facts:

- Each row commits to the hash of the row before it, so alteration propagates and cannot be
  patched over.
- `UPDATE` and `DELETE` are refused by the **database**, not by application code.
- Verification names the offending row — it doesn't just say "invalid".

Then the ALCOA+ mapping from `compliance-matrix.md`, five lines, no more.

### 6 · Pharmacovigilance and the NPvCC
Intake → coding → statutory clock. **State the MedDRA position here, unprompted, before the
compliance slide** — say it in the same tone as everything else, because it is not a confession.

The argument for coding in one sentence: two sites writing *loose motion* and *diarrhoea*
describe one signal and count as none. Then the payoff — STU-004 carries seven cases of pruritus
where nothing else in the portfolio exceeds two.

### 7 · Compliance mapping
The matrix, one screen, dense on purpose. Do not read it aloud; let them scan it and point at
the three rows you want noticed: NDCT 2019, DPDP 2023, MedDRA.

The three-status legend — **Built / Modelled / Deferred** — is the credibility of the slide.
Every framework has a status and none is blank.

### 8 · Deferred scope
Read as staged delivery, not as missing features. Four items, each with its reason:
RBAC and authentication, licensed dictionaries, live EDC/ABDM integration, SDTM export.

Say the RBAC one deliberately: *a presentation-only role switcher would have looked like
access control and enforced nothing, and a fake security control is worse than an absent one.*

### 9 · What comes next
The ordered list from Q&A question 12. Authentication first, because everything else depends on
knowing who is acting.

---

## What is deliberately not in this deck

- **A team slide.** Solo build; say it once in slide 2 and let the scope speak.
- **A technology logo wall.** FastAPI, SQLite and Jinja are not achievements.
- **Screenshots of screens the demo already shows.** Redundant, and they date the moment the
  seed changes.
