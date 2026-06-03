"""
reset_and_run.py
─────────────────
Resets a UPC's pipeline to a clean state from Agent 5 (Writer)
and triggers a fresh run.  Use when units/topics are stuck generating.

Usage:
    python reset_and_run.py 2352283601
    python reset_and_run.py 2352283601 --from-agent 5
"""

import silence_warnings  # noqa: F401 — suppress genai FutureWarning
import argparse
import asyncio
import logging
import sys

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("studyai.reset_run")

from database import queries as q
from database.client import db
from pipeline.orchestrator import run_pipeline


def reset_units(upc: str) -> None:
    """Reset all units for UPC back to queued."""
    units = q.get_units_for_paper(upc)
    for unit in units:
        db.table("units").update({"status": "queued"}).eq("id", unit["id"]).execute()
    log.info("Reset %d units to queued for %s", len(units), upc)


def reset_topics(upc: str) -> None:
    """Reset all topic statuses to queued (keeps content for idempotent skip)."""
    topics = q.get_topics_for_paper(upc)
    stuck = [t for t in topics if t.get("status") in ("generating", "verifying", "failed")]
    for t in stuck:
        db.table("topics").update({"status": "queued"}).eq("id", t["id"]).execute()
    log.info("Reset %d stuck topics to queued for %s", len(stuck), upc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset + re-run StudyAI pipeline")
    parser.add_argument("upc", help="University Paper Code, e.g. 2352283601")
    parser.add_argument(
        "--from-agent", type=int, default=5, metavar="N",
        help="Agent to re-run from (default: 5 = Writer). Use 1 to reset everything."
    )
    args = parser.parse_args()

    upc = args.upc.strip()
    from_agent = args.from_agent

    paper = q.get_paper(upc)
    if not paper:
        log.error("UPC %s not found in database. Run the full pipeline first.", upc)
        sys.exit(1)

    log.info("Resetting pipeline for %s from agent %d", upc, from_agent)

    # Reset stuck statuses
    reset_units(upc)
    reset_topics(upc)

    # Use orchestrator's clear logic for a clean slate from the chosen agent
    q.clear_downstream_from_agent(upc, from_agent)

    log.info("Starting pipeline for %s", upc)
    asyncio.run(run_pipeline(upc))
    log.info("Pipeline complete for %s", upc)


if __name__ == "__main__":
    main()
