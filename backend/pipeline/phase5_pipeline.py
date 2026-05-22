"""
phase5_pipeline.py — Phase 5: Verification & Trust Pipeline
============================================================
Orchestrates Agents 6, 7, and 8 for a single unit after the Writer (Agent 5) completes.

Execution sequence for each unit:
  1. Agent 6 (Coverage Checker / Groq) — runs once per unit on all topics together.
  2. Agent 7 (Verifier / Cerebras + Claude) — runs per topic, only on high-priority topics.
  3. Agent 8 (Critic / Claude Sonnet) — runs per topic, with Agent 6 + 7 results as context.

This module is imported and called by the Orchestrator (pipeline/orchestrator.py).
It does not write to the database directly — it returns a structured result that the
Orchestrator writes.

Output contract (returned dict):
  {
    "unit_id": str,
    "coverage_result": dict,          # Agent 6 output
    "topic_results": [                # One entry per topic
      {
        "topic_id": str,
        "topic_name": str,
        "verifier_result": dict,      # Agent 7 output
        "critic_result": dict,        # Agent 8 output
        "requires_rewrite": bool,     # True if any critical/major corrections exist
        "manual_review": bool,        # True if dual-verification disagreed
      }
    ],
    "phase5_passed": bool,            # True if no topic has critic.failed = True
    "total_corrections": int,
    "total_critical": int,
  }
"""

import logging
from typing import Optional

# Import agents by path — relative imports used in the pipeline package
import importlib
import sys
from pathlib import Path

# Dynamically import agents by their numbered filenames
def _import_agent(filename_stem: str):
    """
    Import an agent module from the agents directory by its filename stem
    (e.g. '06_coverage_checker').
    """
    agents_dir = Path(__file__).resolve().parent / "agents"
    module_path = agents_dir / f"{filename_stem}.py"
    spec = importlib.util.spec_from_file_location(filename_stem, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


logger = logging.getLogger(__name__)


def run_phase5(
    unit_id: str,
    unit_name: str,
    unit_number: int,
    syllabus_topics: list[str],
    generated_topics: list[dict],
) -> dict:
    """
    Run the full Phase 5 pipeline (Agents 6, 7, 8) for one unit.

    Args:
        unit_id: UUID of the unit in Supabase.
        unit_name: Human-readable unit name.
        unit_number: Unit number within the paper.
        syllabus_topics: Topic strings from the extracted syllabus for this unit.
                         Source: units row → topics[] from syllabus_extraction_schema.
        generated_topics: List of fully-generated topic dicts from Agent 5 (Writer).
                          Each must include at minimum:
                            id, topic_name, priority, definition, core_concept,
                            rapid_revision, examples, instruction_word_frequency.

    Returns:
        Structured Phase 5 result dict (see module docstring for contract).
    """
    logger.info(
        "=== Phase 5 starting | unit_id=%s | unit=%d – %s | topics=%d ===",
        unit_id, unit_number, unit_name, len(generated_topics),
    )

    # ── Lazy-load agents ──────────────────────────────────────────────────────
    agent_06 = _import_agent("06_coverage_checker")
    agent_07 = _import_agent("07_verifier")
    agent_08 = _import_agent("08_critic")

    # ────────────────────────────────────────────────────────────────────────
    # STEP 1 — Agent 6: Coverage Checker (unit-level, one call for all topics)
    # ────────────────────────────────────────────────────────────────────────
    logger.info("Phase 5 — Step 1: Coverage Checker | unit_id=%s", unit_id)

    coverage_result = agent_06.run(
        unit_id=unit_id,
        unit_name=unit_name,
        unit_number=unit_number,
        syllabus_topics=syllabus_topics,
        topics=generated_topics,
    )

    if coverage_result.get("skipped"):
        logger.warning(
            "Coverage Checker skipped — Groq unavailable | unit_id=%s | error=%s",
            unit_id, coverage_result.get("error"),
        )
    else:
        logger.info(
            "Coverage Checker done | unit_id=%s | missing=%d | irrelevant=%d",
            unit_id,
            len(coverage_result.get("missing_topics", [])),
            len(coverage_result.get("irrelevant_content", [])),
        )

    # ────────────────────────────────────────────────────────────────────────
    # STEP 2 & 3 — Per-topic: Agent 7 (Verifier) then Agent 8 (Critic)
    # ────────────────────────────────────────────────────────────────────────
    topic_results = []
    total_corrections = 0
    total_critical = 0
    phase5_passed = True

    for topic in generated_topics:
        topic_id = topic.get("id", "unknown")
        topic_name = topic.get("topic_name", "unknown")
        priority = topic.get("priority", "low")

        logger.info(
            "Phase 5 — Topic [%s] | priority=%s", topic_name, priority,
        )

        # ── Step 2: Agent 7 — Verifier ───────────────────────────────────────
        logger.info("  Step 2: Verifier | topic_id=%s", topic_id)
        verifier_result = agent_07.run(topic=topic)

        if not verifier_result.get("fired"):
            logger.info(
                "  Verifier did not fire (priority=%s) | topic_id=%s", priority, topic_id,
            )

        if verifier_result.get("manual_review"):
            logger.warning(
                "  Verifier MANUAL REVIEW required | topic_id=%s | topic=%s",
                topic_id, topic_name,
            )

        # ── Step 3: Agent 8 — Critic ─────────────────────────────────────────
        logger.info("  Step 3: Critic | topic_id=%s", topic_id)
        critic_result = agent_08.run(
            topic=topic,
            coverage_flags=coverage_result,
            verifier_result=verifier_result,
        )

        if critic_result.get("failed"):
            logger.error(
                "  Critic FAILED after retries | topic_id=%s | error=%s",
                topic_id, critic_result.get("error"),
            )
            phase5_passed = False

        corrections_count = critic_result.get("correction_count", 0)
        critical_count = critic_result.get("critical_count", 0)
        major_count = critic_result.get("major_count", 0)

        total_corrections += corrections_count
        total_critical += critical_count

        # A topic requires rewrite if it has any critical or major corrections
        requires_rewrite = (critical_count > 0 or major_count > 0) and not critic_result.get("failed")

        topic_results.append({
            "topic_id": topic_id,
            "topic_name": topic_name,
            "priority": priority,
            "verifier_result": verifier_result,
            "critic_result": critic_result,
            "requires_rewrite": requires_rewrite,
            "manual_review": verifier_result.get("manual_review", False),
        })

        logger.info(
            "  Topic complete | topic=%s | corrections=%d (critical=%d, major=%d) | rewrite=%s",
            topic_name, corrections_count, critical_count, major_count, requires_rewrite,
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    topics_requiring_rewrite = sum(1 for t in topic_results if t["requires_rewrite"])
    topics_manual_review = sum(1 for t in topic_results if t["manual_review"])

    logger.info(
        "=== Phase 5 complete | unit_id=%s | phase5_passed=%s | "
        "total_corrections=%d | total_critical=%d | "
        "topics_requiring_rewrite=%d | topics_manual_review=%d ===",
        unit_id, phase5_passed,
        total_corrections, total_critical,
        topics_requiring_rewrite, topics_manual_review,
    )

    return {
        "unit_id": unit_id,
        "coverage_result": coverage_result,
        "topic_results": topic_results,
        "phase5_passed": phase5_passed,
        "total_corrections": total_corrections,
        "total_critical": total_critical,
        "topics_requiring_rewrite": topics_requiring_rewrite,
        "topics_manual_review": topics_manual_review,
    }


# ── Convenience helpers for Orchestrator ─────────────────────────────────────

def extract_rewrite_targets(phase5_result: dict) -> list[dict]:
    """
    Extract topic results that require rewriting.
    Called by the Orchestrator to feed Agent 9 (Rewriter).

    Returns:
        List of { topic_id, topic_name, critic_corrections } for topics
        where requires_rewrite is True.
    """
    return [
        {
            "topic_id": t["topic_id"],
            "topic_name": t["topic_name"],
            "critic_corrections": t["critic_result"].get("corrections", []),
        }
        for t in phase5_result.get("topic_results", [])
        if t.get("requires_rewrite")
    ]


def extract_manual_review_topics(phase5_result: dict) -> list[dict]:
    """
    Extract topics that require manual review due to dual-verification disagreement.
    Called by the Orchestrator to write manual review flags to the database.

    Returns:
        List of { topic_id, topic_name, reason } for topics where manual_review is True.
    """
    results = []
    for t in phase5_result.get("topic_results", []):
        if not t.get("manual_review"):
            continue
        verifier = t.get("verifier_result", {})
        reason = "Dual numerical verification disagreement."
        results.append({
            "topic_id": t["topic_id"],
            "topic_name": t["topic_name"],
            "reason": reason,
        })
    return results
