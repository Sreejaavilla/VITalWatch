"""Rehearsal harness — walks the demo script and checks every claim it makes out loud.

The failure this prevents is specific and expensive: the demo script says "34% of plan"
and the screen says 41%, because a threshold moved three commits ago and nobody re-read
the script. On stage that reads as not knowing your own system.

So every number spoken in `docs/demo-script.md` is an assertion here. Change the data,
the thresholds or the rules, run this, and it tells you which line of the script is now
a lie.

    python scripts/rehearse.py            # three clean runs, fresh database each time
    python scripts/rehearse.py --runs 1   # one, for a quick check

Each run reseeds from scratch, so this also proves the recovery path three times over.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

PASS, FAIL = "  \033[32mok\033[0m  ", "  \033[31mFAIL\033[0m"


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def __call__(self, name: str, actual, expected=True) -> None:
        ok = (actual == expected) if expected is not True else bool(actual)
        detail = "" if ok else f"   expected {expected!r}, got {actual!r}"
        print(f"{PASS if ok else FAIL}  {name}{detail}")
        if not ok:
            self.failures.append(name)


def reseed() -> None:
    """Back to the pristine seed, whichever engine is configured.

    On SQLite that is deleting the file. On Postgres it is dropping the tables — the
    same operation, and it has to happen here rather than being assumed, or a rehearsal
    against Supabase would silently be checking a database it never reset.
    """
    from app import db as database

    if database.is_postgres():
        conn = database.connect()
        database.reset(conn)
        conn.close()
    else:
        (ROOT / "data" / "ctms.db").unlink(missing_ok=True)

    subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "-m", "app.db"],
        cwd=ROOT, check=True, capture_output=True,
    )


def run_once(run_no: int) -> list[str]:
    from app import db
    from app.main import app

    print(f"\n\033[1mrun {run_no}\033[0m — fresh database")
    reseed()
    check = Check()

    with TestClient(app) as c:
        # ---- beat 1: portfolio
        k = c.get("/api/kpi/portfolio").json()
        check("portfolio: 8 active studies", k["active_studies"], 8)
        check("portfolio: 359 enrolled of 1030", (k["enrolled_total"], k["target_total"]), (359, 1030))
        check("portfolio: 10 of 12 sites activated", (k["sites_activated"], k["sites_total"]), (10, 12))
        check("portfolio: 42 open queries", k["open_queries"], 42)

        alerts = c.get("/api/alerts").json()
        check("portfolio: 9 alerts", len(alerts), 9)
        by_study = {a["study_id"]: a["message"] for a in alerts if a["rule"] == "enrolment_lag"}
        check("STU-001 enrolment at 34% of plan", "34%" in by_study.get("STU-001", ""))
        check("STU-005 enrolment at 41% of plan", "41%" in by_study.get("STU-005", ""))
        check("alerts ranked critical first", alerts[0]["severity"], "critical")

        # ---- beat 2: drill-down
        ec = next((a for a in alerts if a["rule"] == "ethics_renewal_due"), {})
        check("STU-002 ethics expiring in 21 days", "21 days" in ec.get("message", ""))
        check("STU-002 alert deep-links to the study", ec.get("deep_link"), "/study/STU-002")
        check("STU-003 flags enrolling without CTRI",
              "Enrolling without a CTRI registration number" in c.get("/study/STU-003").text)

        # ---- beat 3: file a serious AE
        before = c.get("/api/audit/verify").json()
        check("chain intact before filing", before["ok"] and before["count"] == 9)

        filed = c.post("/ae", data={
            "study_id": "STU-002", "subject_code": "AIIA-002-004",
            "onset_date": "2026-08-22",
            "narrative": "severe diarhea and dehydration since last night",
            "severity": "severe", "causality": "probable",
            "outcome": "recovering", "serious": "true",
        }, follow_redirects=True)
        check("AE filed", filed.status_code, 200)
        page = filed.text
        check("coded to Diarrhoea", "Diarrhoea" in page)
        check("coded VW-T0012", "VW-T0012" in page)
        check("confidence 0.93", "0.93" in page)
        check("source reads curated, not MedDRA", "source curated" in page)
        check("24-hour clock started", "24.0 hours to the 24-hour deadline" in page)

        clocks = {}
        for e in c.get("/api/signals").json(), :  # touch the endpoint; counts below use SQL
            pass
        from app.db import connect
        conn = connect()
        for row in conn.execute(
            "SELECT timeline_status, COUNT(*) n FROM adverse_events WHERE serious=1 GROUP BY 1"
        ):
            clocks[row["timeline_status"]] = row["n"]
        check("2 SAEs already breached", clocks.get("breached"), 2)
        check("1 SAE due soon", clocks.get("due_soon"), 1)

        # ---- beat 4: safety signals
        sig = c.get("/api/signals?min_cases=2").json()["signals"]
        top = sig[0]
        check("top signal is STU-004 Pruritus", (top["study_id"], top["coded_term"]),
              ("STU-004", "Pruritus"))
        check("pruritus has 7 cases", top["cases"], 7)
        check("pruritus is flagged", top["flagged"], True)
        check("pruritus unseen elsewhere (c = 0)", top["contingency"]["c"], 0)

        arth = next((s for s in sig if s["coded_term"] == "Arthralgia"), None)
        check("Arthralgia row present", arth is not None)
        if arth:
            # 15.33, not the 14.0 the untouched database shows: the AE filed in beat 3
            # lands in STU-002 and shifts the portfolio denominator. The number visibly
            # moves during the demo, which is worth knowing before it happens on stage —
            # so the script says "over 14" rather than quoting two decimal places.
            check("Arthralgia PRR is over 15 after the demo AE", arth["prr"], 15.33)
            check("Arthralgia NOT flagged (2 cases)", arth["flagged"], False)
        check("Pruritus still tops the ranking after filing",
              (sig[0]["study_id"], sig[0]["coded_term"]), ("STU-004", "Pruritus"))

        # ---- role lenses: the same figures, selected for three different readers
        for rid in ("investigator", "safety", "leadership"):
            k = c.get(f"/api/kpi/role/{rid}").json()
            check(f"{rid} lens returns six metrics", len(k["metrics"]), 6)
            check(f"{rid} lens defines every metric",
                  all(m["definition"] for m in k["metrics"]))
            page = c.get(f"/role/{rid}")
            check(f"{rid} lens states it is not access control",
                  "not access control" in page.text)

        # A non-zero count beside a subtitle saying there is nothing is the failure this
        # guards: the one flagged signal has an undefined PRR, which an ordering by PRR
        # alone silently drops.
        sig_metric = next(m for m in c.get("/api/kpi/role/safety").json()["metrics"]
                          if m["label"] == "Signals above threshold")
        check("safety lens counts both flagged signals", sig_metric["value"], "2")
        check("safety lens names it rather than reporting nothing",
              "Pruritus" in (sig_metric["sub"] or ""))

        # Scoped to a real PI, not the whole portfolio wearing a different heading.
        inv = c.get("/api/kpi/role/investigator?pi=Dr.+V.+Sharma").json()
        check("investigator lens scopes to the PI asked for", inv["scope"], "Dr. V. Sharma")
        check("unknown PI falls back rather than erroring",
              c.get("/role/investigator?pi=nobody").status_code, 200)

        # ---- clinical investigation: the case, the cluster, the retrieval, the decision
        case = c.get("/api/investigation/INV-001").json()
        check("investigation case renders", c.get("/investigation").status_code, 200)
        check("investigation board renders",
              c.get("/investigation/INV-001").status_code, 200)
        check("unknown case is a 404", c.get("/investigation/NOPE").status_code, 404)

        cl = case["cluster"]
        check("cluster is 3 events", cl["size"], 3)
        check("all three coded to one term", cl["coded_term"], "Hepatic enzyme increased")
        check("three different narratives, one code", cl["coded_code"], "VW-T0029")
        check("exposure window day 41-49",
              (cl["first_day_on_treatment"], cl["last_day_on_treatment"]), (41, 49))
        # The line the demo turns on: close in exposure, far apart on the calendar.
        check("8 days apart on treatment", cl["exposure_span_days"], 8)
        check("126 days apart by calendar", cl["calendar_span_days"], 126)
        check("system states what it does not claim", len(case["not_claimed"]), 3)
        check("no causal claim anywhere in the case",
              not any("caused" in o.lower() for o in case["observations"]))

        inv_kpi = c.get("/api/kpi/study/AYU-008").json()
        check("AYU-008 enrolment 137 of 500",
              (inv_kpi["enrolled"], inv_kpi["target"]), (137, 500))
        check("AYU-008 plan-to-date is 240", inv_kpi["expected_by_today"], 240)

        # Retrieval: BM25 finds nothing for wording that is in no document, and the
        # concept retriever carries it. This is the RRF beat and it must stay true.
        ret = c.get("/api/investigation/INV-001/retrieve?q=deranged+LFT").json()
        check("BM25 finds nothing for 'deranged LFT'",
              len(ret["retrievers"]["bm25"]["results"]), 0)
        check("concept expansion finds it anyway",
              len(ret["retrievers"]["concept"]["results"]) > 0)
        check("fusion still returns a ranking", len(ret["fusion"]["results"]) > 0)
        check("second retriever is not called dense",
              "not a dense model" in ret["retrievers"]["concept"]["kind"])

        # The decision, and the audit row it must be written with.
        seq_before = c.get("/api/audit/verify").json()["count"]
        posted = c.post("/investigation/INV-001/decision", data={
            "action": "escalate",
            "reason": "Potential emerging safety pattern requiring further assessment.",
            "evidence_count": 7,
        }, follow_redirects=False)
        check("decision accepted", posted.status_code, 303)
        after_decision = c.get("/api/audit/verify").json()
        check("decision appended exactly one audit row",
              after_decision["count"], seq_before + 1)
        check("chain still intact after the decision", after_decision["ok"])
        check("decision is visible on the board",
              "Decision recorded" in c.get("/investigation/INV-001").text)
        check("a decision without a known action is refused",
              c.post("/investigation/INV-001/decision",
                     data={"action": "bogus", "reason": "x"}).status_code, 400)

        # ---- beat 5: audit
        after = c.get("/api/audit/verify").json()
        check("chain intact after filing, 11 events", after["ok"] and after["count"] == 11)
        check("audit page renders", c.get("/audit?verify=1").status_code, 200)
        check("audit filters by actor", "2 of 11" in c.get("/audit?actor=demo.operator").text)

        # ---- beat 6, first half: the storage layer refuses the edit outright.
        # Engine-dependent since the move to Postgres — SQLite raises from a trigger
        # body, Postgres from a trigger function — so it gets asserted rather than
        # assumed. This is what the demo claims out loud before anything is dropped.
        for operation, sql in (
            ("UPDATE", "UPDATE audit_events SET actor='mallory' WHERE seq=1"),
            ("DELETE", "DELETE FROM audit_events WHERE seq=1"),
        ):
            try:
                conn.execute(sql)
                conn.commit()
                refused = ""
            except Exception as exc:  # noqa: BLE001 — any refusal is the pass condition
                refused = str(exc)
                conn.rollback()
            check(f"storage layer refuses {operation}", "append-only" in refused)

        # ---- beat 6, second half: drop the guard, and the chain still catches it
        db.drop_audit_guard(conn)
        conn.execute("UPDATE audit_events SET after_json='{}' WHERE seq=3")
        conn.commit()
        broken = c.get("/api/audit/verify").json()
        check("tamper detected", broken["ok"], False)
        check("names the altered row (seq 3)", broken.get("seq"), 3)
        check("says content altered", "content altered" in broken.get("error", ""))
        check("audit page shows the break",
              "Chain broken at sequence 3" in c.get("/audit").text)
        conn.close()

        # ---- every route a judge might click
        for path in ("/", "/portfolio", "/study/STU-004", "/ae", "/signals", "/audit",
                     "/health", "/docs", "/api/fhir/ResearchStudy/STU-001",
                     "/api/export/sdtm/dm.csv",
                     "/role/investigator", "/role/safety", "/role/leadership",
                     "/api/kpi/role/leadership", "/investigation", "/investigation/INV-001",
                     "/api/investigation/INV-001"):
            check(f"route {path}", c.get(path).status_code, 200)

    return check.failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3,
                        help="clean end-to-end runs (the roadmap says three, not two)")
    args = parser.parse_args()

    all_failures: list[tuple[int, str]] = []
    for i in range(1, args.runs + 1):
        all_failures += [(i, f) for f in run_once(i)]

    print("\n" + "=" * 60)
    reseed()  # leave the database pristine, whatever happened above
    if all_failures:
        print(f"\033[31m{len(all_failures)} failed check(s)\033[0m across {args.runs} run(s):")
        for run_no, name in all_failures:
            print(f"  run {run_no}: {name}")
        print("\nEvery check here is a line in docs/demo-script.md. Fix the app or fix the script.")
        return 1
    print(f"\033[32mall checks passed — {args.runs} clean run(s)\033[0m")
    print("The demo script matches the application. Database left at the pristine seed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
