"""
backend/database/queries.py
────────────────────────────
Single source of truth for every database read and write in the pipeline.
No agent ever calls `db` directly — they import a function from here.

Sections:
  1. Papers
  2. Units
  3. Topics
  4. Pipeline state helpers (used by orchestrator for resume logic)
"""

from __future__ import annotations

import logging
from typing import Any

from database.client import db

log = logging.getLogger("studyai.db")


# ─────────────────────────────────────────────────────────────────────────────
# 1. PAPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_paper(upc: str) -> dict | None:
    """Return the full papers row for a UPC, or None if not found."""
    res = db.table("papers").select("*").eq("upc", upc).execute()
    return res.data[0] if res.data else None


def upsert_paper(upc: str, data: dict) -> dict:
    """Insert or update the papers row.  Returns the saved row."""
    payload = {"upc": upc, **data}
    res = db.table("papers").upsert(payload, on_conflict="upc").execute()
    return res.data[0]


def set_paper_status(upc: str, status: str) -> None:
    """Set pipeline_status on the papers row."""
    db.table("papers").update({"pipeline_status": status}).eq("upc", upc).execute()
    log.info("paper %s → pipeline_status=%s", upc, status)


def set_paper_dna(upc: str, paper_dna: dict) -> None:
    """Write the assembled Paper DNA blob to papers.paper_dna."""
    db.table("papers").update({"paper_dna": paper_dna}).eq("upc", upc).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 2. UNITS
# ─────────────────────────────────────────────────────────────────────────────

def get_units_for_paper(upc: str) -> list[dict]:
    """Return all unit rows for a paper, ordered by unit_number."""
    res = (
        db.table("units")
        .select("*")
        .eq("upc", upc)
        .order("unit_number")
        .execute()
    )
    return res.data or []


def get_unit(unit_id: str) -> dict | None:
    res = db.table("units").select("*").eq("id", unit_id).execute()
    return res.data[0] if res.data else None


def create_unit(upc: str, unit_number: int, unit_name: str,
                estimated_study_hours: float | None = None,
                marks_weightage: int | None = None) -> dict:
    """Insert a unit row and return it."""
    payload = {
        "upc": upc,
        "unit_number": unit_number,
        "unit_name": unit_name,
        "status": "queued",
    }
    if estimated_study_hours is not None:
        payload["estimated_study_hours"] = estimated_study_hours
    if marks_weightage is not None:
        payload["marks_weightage"] = marks_weightage
    res = db.table("units").insert(payload).execute()
    return res.data[0]


def set_unit_status(unit_id: str, status: str) -> None:
    """Transition a unit's status field."""
    db.table("units").update({"status": status}).eq("id", unit_id).execute()
    log.info("unit %s → status=%s", unit_id, status)


def save_unit_summary(unit_id: str, conceptual_summary: dict,
                      unit_closer: dict) -> None:
    """Write unit-level summary fields after patching is complete."""
    db.table("units").update({
        "conceptual_summary": conceptual_summary,
        "unit_closer": unit_closer,
    }).eq("id", unit_id).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 3. TOPICS
# ─────────────────────────────────────────────────────────────────────────────

def get_topics_for_unit(unit_id: str) -> list[dict]:
    """Return all topics for a unit, ordered by topic_number."""
    res = (
        db.table("topics")
        .select("*")
        .eq("unit_id", unit_id)
        .order("topic_number")
        .execute()
    )
    return res.data or []


def get_topics_for_paper(upc: str) -> list[dict]:
    """Return every topic across all units for a paper (used by Agent 12)."""
    res = (
        db.table("topics")
        .select("*")
        .eq("upc", upc)
        .order("topic_number")
        .execute()
    )
    return res.data or []


def get_topic(topic_id: str) -> dict | None:
    res = db.table("topics").select("*").eq("id", topic_id).execute()
    return res.data[0] if res.data else None


def create_topic(unit_id: str, upc: str, topic_name: str,
                 topic_number: int) -> dict:
    """Create a bare topic row (agents fill in content fields later)."""
    payload = {
        "unit_id": unit_id,
        "upc": upc,
        "topic_name": topic_name,
        "topic_number": topic_number,
        "status": "queued",
    }
    res = db.table("topics").insert(payload).execute()
    return res.data[0]


def set_topic_status(topic_id: str, status: str) -> None:
    db.table("topics").update({"status": status}).eq("id", topic_id).execute()
    log.info("topic %s → status=%s", topic_id, status)


def save_topic_content(topic_id: str, content: dict) -> None:
    """
    Write the full Writer JSON output into the topic's content columns.
    The content dict uses the same field names as the topics table.
    """
    # Map top-level keys directly; Supabase accepts JSONB as Python dicts.
    allowed_fields = {
        "difficulty", "estimated_study_minutes", "priority",
        "depth_signal_source", "rapid_revision",
        "definition", "core_concept", "analogy", "analogy_verified",
        "examples", "diagram_block",
        "examiners_note", "examiners_note_pyq_refs", "instruction_word_frequency",
        "common_mistakes", "answer_writing_technique",
        "pyqs", "quick_checks", "connects_to_reason", "flagged_fields",
    }
    payload = {k: v for k, v in content.items() if k in allowed_fields}
    payload["status"] = "complete"
    db.table("topics").update(payload).eq("id", topic_id).execute()


def save_topic_patch(topic_id: str, patched_fields: dict) -> None:
    """Apply a patcher patch to a topic (field-level updates only)."""
    patched_fields["patched"] = True
    db.table("topics").update(patched_fields).eq("id", topic_id).execute()


def set_topic_prerequisite(topic_id: str, prerequisite_topic_id: str,
                            bridge: str) -> None:
    db.table("topics").update({
        "prerequisite_topic_id": prerequisite_topic_id,
        "prerequisite_bridge": bridge,
    }).eq("id", topic_id).execute()


def set_topic_connects_to(topic_id: str, connects_to_id: str,
                           reason: str) -> None:
    db.table("topics").update({
        "connects_to_topic_id": connects_to_id,
        "connects_to_reason": reason,
    }).eq("id", topic_id).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 4. PIPELINE STATE HELPERS  (used by orchestrator resume logic)
# ─────────────────────────────────────────────────────────────────────────────

def paper_has_syllabus(upc: str) -> bool:
    """True if the papers row exists and has unit-level data already seeded."""
    row = get_paper(upc)
    if not row:
        return False
    units = get_units_for_paper(upc)
    return len(units) > 0


def paper_has_dna(upc: str) -> bool:
    """True if paper_dna has been populated."""
    row = get_paper(upc)
    return bool(row and row.get("paper_dna"))


def units_have_mapper_data(upc: str) -> bool:
    """True if topics exist with prerequisite/sequence data (Agent 4 output)."""
    topics = get_topics_for_paper(upc)
    if not topics:
        return False
    # At least one topic should have topic_number > 0 from the mapper resequencing
    return any(t.get("topic_number") is not None for t in topics)


def topic_has_content(topic_id: str) -> bool:
    """True if Writer has already completed this topic."""
    topic = get_topic(topic_id)
    return bool(topic and topic.get("definition"))


def get_incomplete_units(upc: str) -> list[dict]:
    """Return units that are not yet 'complete' (used for resume)."""
    res = (
        db.table("units")
        .select("*")
        .eq("upc", upc)
        .neq("status", "complete")
        .order("unit_number")
        .execute()
    )
    return res.data or []


def get_incomplete_topics(unit_id: str) -> list[dict]:
    """Return topics in a unit that still need writing."""
    res = (
        db.table("topics")
        .select("*")
        .eq("unit_id", unit_id)
        .neq("status", "complete")
        .order("topic_number")
        .execute()
    )
    return res.data or []


def clear_downstream_from_agent(upc: str, from_agent: int) -> None:
    """
    Force-rerun support.  Clears data fields so the orchestrator re-runs
    from the specified agent number.  Used by --force-rerun-from CLI flag.

    Agent numbers:
      3 → clear paper_dna
      4 → clear topic prerequisite / sequence data
      5 → clear all topic content
      6+ → clear topic statuses back to 'queued'
    """
    if from_agent <= 3:
        db.table("papers").update({"paper_dna": None}).eq("upc", upc).execute()

    if from_agent <= 4:
        # Reset topic sequence/prerequisite data
        topics = get_topics_for_paper(upc)
        for t in topics:
            db.table("topics").update({
                "prerequisite_topic_id": None,
                "prerequisite_bridge": None,
                "connects_to_topic_id": None,
                "connects_to_reason": None,
                "split_generation": False,
            }).eq("id", t["id"]).execute()

    if from_agent <= 5:
        # Wipe content fields and status on all topics
        content_fields = {
            "definition": None, "core_concept": None, "analogy": None,
            "rapid_revision": None, "examples": None, "diagram_block": None,
            "examiners_note": None, "common_mistakes": None,
            "answer_writing_technique": None, "pyqs": None,
            "quick_checks": None, "status": "queued",
        }
        topics = get_topics_for_paper(upc)
        for t in topics:
            db.table("topics").update(content_fields).eq("id", t["id"]).execute()
        # Reset all unit statuses
        db.table("units").update({"status": "queued"}).eq("upc", upc).execute()

    if from_agent <= 12:
        db.table("papers").update({"pipeline_status": "queued"}).eq("upc", upc).execute()

    log.warning("Force-rerun: cleared data from agent %d onwards for %s", from_agent, upc)