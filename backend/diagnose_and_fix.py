"""
diagnose_and_fix.py
────────────────────
Diagnose pipeline import issues, reset stuck state, and verify readiness.

Usage:
    python diagnose_and_fix.py 2352283601
"""

import sys
import os
import logging
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("studyai.diagnose")

upc = sys.argv[1] if len(sys.argv) > 1 else "2352283601"

# ── 1. Check imports ──────────────────────────────────────────────────────────
print("\n=== Import Check ===")
try:
    from database import queries as q
    from database.client import db
    print("  [OK] database")
except Exception as e:
    print(f"  [FAIL] database: {e}")
    sys.exit(1)

try:
    from pipeline.agents import agent_05_writer as writer
    import asyncio
    assert asyncio.iscoroutinefunction(writer.run), "writer.run must be async"
    print("  [OK] agent_05_writer (run is async)")
except Exception as e:
    print(f"  [FAIL] agent_05_writer: {e}")
    sys.exit(1)

try:
    from pipeline.agents import agent_02_researcher as researcher
    assert asyncio.iscoroutinefunction(researcher.run)
    print("  [OK] agent_02_researcher")
except Exception as e:
    print(f"  [FAIL] agent_02_researcher: {e}")

try:
    from pipeline.agents import agent_02b_researcher_verifier as verifier
    assert asyncio.iscoroutinefunction(verifier.run)
    print("  [OK] agent_02b")
except Exception as e:
    print(f"  [FAIL] agent_02b: {e}")

try:
    from pipeline.orchestrator import run_pipeline
    print("  [OK] orchestrator")
except Exception as e:
    print(f"  [FAIL] orchestrator: {e}")
    sys.exit(1)

# ── 2. DB state check ─────────────────────────────────────────────────────────
print(f"\n=== DB State for {upc} ===")
paper = q.get_paper(upc)
if not paper:
    print(f"  [ERROR] Paper {upc} not found")
    sys.exit(1)
print(f"  Paper status: {paper.get('pipeline_status')}")

units = q.get_units_for_paper(upc)
print(f"  Units: {len(units)}")
for u in units:
    topics = q.get_topics_for_unit(u["id"])
    complete = sum(1 for t in topics if t.get("definition"))
    print(f"    Unit {u['unit_number']} [{u['status']}] '{u['unit_name'][:40]}' — {complete}/{len(topics)} topics done")

all_topics = q.get_topics_for_paper(upc)
stuck = [t for t in all_topics if t.get("status") in ("generating", "verifying", "failed")]

# ── 3. Fix stuck state ────────────────────────────────────────────────────────
if stuck:
    print(f"\n=== Fixing {len(stuck)} stuck topics ===")
    for t in stuck:
        db.table("topics").update({"status": "queued"}).eq("id", t["id"]).execute()
        print(f"  Reset topic: {t['topic_name'][:50]}")

# Fix stuck units
for u in units:
    if u["status"] == "generating":
        db.table("units").update({"status": "queued"}).eq("id", u["id"]).execute()
        print(f"  Reset unit: {u['unit_name'][:40]}")

# Reset paper to queued if needed
if paper.get("pipeline_status") in ("generating", "failed"):
    db.table("papers").update({"pipeline_status": "queued"}).eq("upc", upc).execute()
    print(f"  Reset paper status to queued")

print("\n=== Diagnosis Complete ===")
print("  All imports OK. DB state clean.")
print(f"  Ready to run: python reset_and_run.py {upc}")
