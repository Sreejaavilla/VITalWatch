# Cue card — one page, for the podium

Full wording in `demo-script.md`. This is the version you can actually glance at.

**Before you start:** `./scripts/rehearse.py` green · app running · tabs `/` `/portfolio` `/ae` `/signals` `/audit` · terminal on screen 2 with the tamper commands typed · video tab open ·
notifications off.

---

| # | Screen | The line that matters | Time |
|---|---|---|---|
| 0 | `/` |  *(optional)* synthetic data · not MedDRA · then click **Portfolio** | 0:15 |
| 1 | `/portfolio` | 7 studies · 222 of 530 · **8 alerts, thresholds from config** · lag is vs **plan-to-date**, not final target | 0:45 |
| 2 | click EC alert → `/study/STU-002` | approval expires in **21 days** — a lapsed approval is a **stop-work condition** | 0:40 |
| 3 | `/ae` — type it live | `severe diarhea and dehydration since last night` · STU-002 · AIIA-002-004 · severe · probable · **tick Serious** | 1:10 |
| | | → **Diarrhoea VW-T0012, 0.93, through a typo** · source says **curated, not MedDRA** · **24-hour clock, NDCT 2019** | |
| 4 | `Safety signals →` | **STU-004 pruritus, 7 cases, 70%, nowhere else** · then: Arthralgia scores **over 14 and is NOT flagged** — two cases, arithmetic not evidence | 0:45 |
| 5 | `/audit` → **Verify chain** | every change, before and after · **9 events from genesis** · green | 0:40 |
| 6 | terminal | UPDATE **refused by the database** → drop trigger → UPDATE → reload → **"Chain broken at sequence 3"** — *it names the row* | 0:45 |
| 7 | — | one auditable view · clocks running · log that cannot be quietly edited · **no name field to put real data into** | 0:20 |

**Runs 5:20. Cuts in order:** beat 0, then beat 2's CTRI aside → beat 4's Arthralgia counter-example →
beat 2 entirely. **Never cut beat 6.**

---

### Say these before you are asked
- **"That's not MedDRA"** — beat 3, unprompted. 72 terms we wrote, `source: curated` on screen.
- **"No authentication, and that was a decision"** — half a sentence, early. A fake role
  switcher would be worse than none.
- **"Every record is synthetic"** — the close.

### The three numbers not to fumble
**8** alerts · **7** pruritus cases · **sequence 3** is where the chain breaks.

### If it breaks
Page 500s → reload once, then move on. Data looks wrong → `./scripts/seed.sh`, two seconds.
App dead → video tab, keep narrating, apologise once.

### Recovery commands
```bash
./scripts/seed.sh                                    # rebuild identical data
lsof -t -nP -iTCP:8000 -sTCP:LISTEN | xargs kill     # port already in use
```
