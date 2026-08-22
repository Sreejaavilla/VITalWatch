# Demo script — 4 minutes

Locked at hour 15. The video is recorded against this, word for word. **Never deviate from
the path on stage.** Every number below is real output from the seeded database; the seed is
fixed, so what you rehearse is what the judges see.

There is no login. That is deliberate and you should say so once, early, in half a sentence:
*"authentication is modelled but not enforced — I'll come back to that."* Saying it first
turns a hole into a decision.

---

## Pre-flight — 10 minutes before

- [ ] `./scripts/seed.sh` then `./scripts/run.sh`, and load every screen once so nothing is cold
- [ ] `http://localhost:8000/portfolio` open; `/ae`, `/signals` and `/audit` in tabs 2–4
- [ ] `./scripts/deploy_check.sh` green — 13 endpoints, and it warms every page
- [ ] A terminal on screen 2, already `cd`'d into the repo, with the tamper commands **typed but
      not entered** (see beat 6)
- [ ] Backup video open in a fourth tab, confirmed playing with wifi off
- [ ] Browser zoom at 110%, notifications off, laptop charging

If the app misbehaves in pre-flight: `rm data/ctms.db && ./scripts/run.sh` rebuilds the entire
portfolio from the generator in about two seconds. Every number comes back identical.

---

## The path

### 1 · Portfolio — 45 seconds
**Open `/portfolio`.**

> "This is every trial at AIIA on one screen. Seven active studies, 222 subjects enrolled
> against a target of 530, ten of twelve sites activated, 42 open queries."

Point at the alerts panel.

> "Eight alerts, ranked by severity, and none of these thresholds are hardcoded — they come
> from the environment. STU-001 is at 34% of where the recruitment plan says it should be
> *today*, not 34% of its final target. That distinction is the whole point: a study four
> months into a two-year window at 20% is fine. This one is twenty months in."

### 2 · Drill down — 40 seconds
**Click the STU-002 ethics alert.** It lands you inside the study.

> "Ethics approval expires in 21 days. A study whose approval lapses while it is still
> recruiting has no clearance to be recruiting under — that is a stop-work condition, not a
> reminder, so the system counts down to it."

Scroll to enrolment and deviations.

> "Enrolment against plan-to-date, sites, milestone timeline, and protocol deviations —
> including the ones that were never reported to the ethics committee, flagged as such."

*(If you have time and only if: **STU-003 is enrolling with no CTRI number.** Red banner at the
top of that study. CTRI registration is mandatory *before* the first subject is enrolled. It is
the single most India-specific finding in the demo and judges from the domain will recognise it.)*

### 3 · File a serious adverse event — 70 seconds
**Open `/ae`.** Fill the form in front of them. Type the narrative **with the typo** — it is
there on purpose:

```
severe diarhea and dehydration since last night
```

Study `STU-002`, subject `AIIA-002-004`, onset today, severity `severe`, causality `probable`,
**tick Serious**, submit.

> "That free text just coded to **Diarrhoea, VW-T0012, confidence 0.93** — through a misspelling,
> because sites type the way people type. And note the source reads *curated*, not MedDRA. I'll
> come back to that in one slide.
>
> And ticking 'serious' started a statutory clock. Under the New Drugs and Clinical Trials
> Rules 2019, a serious adverse event has to reach the Ethics Committee and the licensing
> authority within **24 hours**, with a full narrative within 14 days. That banner is now
> counting down from 24.
> Two events in this portfolio have already breached that deadline, one is due within six
> hours — the red and amber badges in the table."

### 4 · The safety signal — 45 seconds
**Click `Safety signals →`.**

> "Coding is not bureaucracy — this screen is what it was for. Two sites writing 'loose motion'
> and 'diarrhoea' describe one safety signal and count as none until both carry the same term.
>
> Top row: **STU-004, pruritus, seven cases** — 70% of that study's coded events, against a term
> that appears nowhere else in the portfolio. Invisible in free text. Obvious once it's coded.
> That is a Data Safety Monitoring Board's first agenda item."

Then point at the Arthralgia row — **this is the line that earns the domain marks**:

> "And look at what's *not* flagged. That row has a ratio over 14, the highest number on the
> screen, and the system deliberately ignores it — two cases. Below three, that ratio is
> arithmetic rather than evidence. The threshold is PRR of 2 with at least 3 cases, which is the
> conventional screen, and the 2×2 table it comes from is at the bottom of the page.
>
> The panel on the right is what this does *not* claim: it's not an incidence rate, because the
> denominator is other reports rather than patients exposed, and it's not causation. It produces
> a triage order for a human."

### 5 · Audit trail — 40 seconds
**Open `/audit`.**

> "Every change, in order, with what the record looked like before and after — including the
> event I filed sixty seconds ago. Each row stores the hash of the row before it."

**Press Verify chain.** Green.

> "Nine events verified from genesis."

### 6 · Break it — 45 seconds · *this is the demo*
**Switch to the terminal.** The commands are already typed.

> "The claim every CTMS makes is that its audit trail is immutable. Watch me test mine."

```bash
sqlite3 data/ctms.db "UPDATE audit_events SET after_json='{}' WHERE seq=3;"
```

> "Rejected by the database itself — a trigger, not application code. So the application being
> compromised doesn't help you. Let me drop the trigger and try again as if I were the DBA."

```bash
sqlite3 data/ctms.db "DROP TRIGGER audit_events_no_update;
                      UPDATE audit_events SET after_json='{}' WHERE seq=3;"
```

**Back to `/audit`. Press Verify chain.** Red.

> "*Chain broken at sequence 3 — content altered.* It doesn't just say something is wrong. It
> names the row. That is the difference between a log you assert is trustworthy and one you can
> prove is."

**Restore before you leave the terminal:** `./scripts/seed.sh`

### 7 · Close — 20 seconds

> "One auditable view of the whole trial lifecycle, from portfolio down to a single adverse
> event — with statutory clocks running, alerts on configurable thresholds, and a log that
> cannot be quietly edited. Every record is synthetic. There is no name field on a subject to
> put a real one into."

---

## Timing

| Beat | Target | Cumulative |
|---|---|---|
| 1 Portfolio | 0:45 | 0:45 |
| 2 Drill down | 0:40 | 1:25 |
| 3 File an SAE | 1:10 | 2:35 |
| 4 Safety signal | 0:45 | 3:20 |
| 5 Audit trail | 0:40 | 4:00 |
| 6 Break it | 0:45 | 4:45 |
| 7 Close | 0:20 | 5:05 |

Over by a minute, so the cuts get decided now rather than on stage. **Cut beat 2's CTRI aside
first** (−15s), then **the second half of beat 4** — keep the pruritus finding, drop the
Arthralgia counter-example (−25s), then **beat 2 entirely** (−40s), landing at 3:45.

Do not cut beat 6 for any reason. If the room is engaged and you are running long, over-running
on beats 4 and 6 is the right way to over-run.

## If something fails on stage

| Failure | Do this |
|---|---|
| A page 500s | Reload once. If it repeats, move to the next beat and come back only if time allows. |
| The database is wrong after the tamper demo | `./scripts/seed.sh` — two seconds, identical data. |
| The whole app is down | Switch to the video tab. Keep narrating live over it; do not apologise twice. |
| You lose your place | Go to `/portfolio`. Every beat can be restarted from there. |
