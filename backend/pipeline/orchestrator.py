"""
backend/pipeline/orchestrator.py
──────────────────────────────────
Runs the full 12-agent pipeline for a single UPC.

Called by main.py as a FastAPI background task.
Also runnable directly:
    python -m pipeline.orchestrator BSCMT201
    python -m pipeline.orchestrator BSCMT201 --force-rerun-from=5

Architecture
────────────
  Phase A — Pre-generation (serial, fast ~60-90s)
    Agent 1  Decoder          — UPC lookup, papers row bootstrap
    Agent 2  Researcher       — Syllabus extraction + PYQ search
    Agent 2B Researcher Verif — Binary pass/fail on syllabus JSON
    Agent 2C PYQ Normaliser   — Normalise all raw PYQ papers
    Agent 3  Paper DNA        — Structural + Topic + Language + Combination DNA
    Agent 4  Mental Mapper    — Dependency graph, sequence, concept bridges

  Phase B — Content generation (parallel across units and topics)
    Agent 5  Writer           — One call per topic (parallel)
    Agent 6  Coverage Checker — Per unit, after Writer finishes unit
    Agent 7  Verifier         — Per topic (proof + numerical, parallel)
    Agent 8  Critic           — Per topic (parallel)
    Agent 9  Rewriter         — Per topic (sequential within topic)
    Agent 9B Micro-Validator  — Per rewritten field

  Phase C — Coverage and patching (serial per unit, then paper-level)
    Agent 10 Final Examiner   — PYQ + marks coverage check (per unit)
    Agent 11 Patcher          — Add missing PYQs + fields
    Agent 11B Post-Patch Regen — Rapid revision, quick_checks, summary
    Agent 12 Consistency Chkr — Cross-topic notation / definition / PYQ year

Status flow
───────────
  papers.pipeline_status : queued → generating → complete / failed / partial
  units.status           : queued → generating → verifying → complete / failed
  topics.status          : queued → generating → complete / failed
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from typing import Any

from database import queries as q
from database.client import db
from utils.cost_tracker import CostTracker, CostKillSwitchError
from utils.rate_limiter import RateLimiter

# ── Agent imports (each module exposes a single async `run(...)` coroutine) ──
from pipeline.agents import (
    agent_01_decoder as decoder,
    agent_02_researcher as researcher,
    agent_02b_researcher_verifier as researcher_verifier,
    agent_02c_pyq_normaliser as pyq_normaliser,
    agent_04_mental_model_mapper as mapper,
    agent_05_writer as writer,
    agent_06_coverage_checker as coverage_checker,
    agent_07_verifier as verifier,
    agent_08_critic as critic,
    agent_09_rewriter as rewriter,
    agent_09b_micro_validator as micro_validator,
    agent_10_final_examiner as final_examiner,
    agent_11_patcher as patcher,
    agent_11b_post_patch_regen as post_patch_regen,
    agent_12_consistency_checker as consistency_checker,
)
from pipeline.agents.agent_03_paper_dna import (
    structural_dna,
    topic_dna,
    language_dna,
    combination_dna,
)

log = logging.getLogger("studyai.orchestrator")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MAX_WRITER_RETRIES = 3
MAX_CRITIC_RETRIES = 2
MAX_VERIFIER_RETRIES = 2
MAX_EXAMINER_RETRIES = 2
MAX_PATCHER_RETRIES = 2
MAX_UNIT_RESUME_ATTEMPTS = 3

# Semaphore limits match rate_limiter.py provider caps
_FLASH_SEM = asyncio.Semaphore(5)   # Gemini 2.0 Flash  (Writer + Critic)
_PRO_SEM = asyncio.Semaphore(2)     # Gemini Pro        (DNA + Mapper + Verifier)
_GROQ_SEM = asyncio.Semaphore(3)    # Groq Llama 3
_CEREBRAS_SEM = asyncio.Semaphore(3)  # Cerebras

rate_limiter = RateLimiter()

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline(upc: str, force_rerun_from: int | None = None) -> None:
    """
    Main pipeline coroutine.  Called by FastAPI as a background task.
    `force_rerun_from` sets the agent number to re-run from (clears downstream).
    """
    log.info("═══ Pipeline start: %s ═══", upc)
    cost = CostTracker(upc)

    if force_rerun_from is not None:
        log.warning("Force rerun from agent %d for %s", force_rerun_from, upc)
        q.clear_downstream_from_agent(upc, force_rerun_from)

    q.set_paper_status(upc, "generating")

    try:
        await _phase_a_pre_generation(upc, cost)
        await _phase_b_content_generation(upc, cost)
        await _phase_c_coverage_and_patching(upc, cost)

        q.set_paper_status(upc, "complete")
        log.info("═══ Pipeline complete: %s  cost=$%.4f ═══", upc, cost.total_usd)

    except CostKillSwitchError as exc:
        log.error("Cost kill switch triggered for %s: %s", upc, exc)
        q.set_paper_status(upc, "partial")

    except _PipelineHaltError as exc:
        log.error("Pipeline halted for %s: %s", upc, exc)
        q.set_paper_status(upc, "failed")

    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected pipeline crash for %s", upc)
        # Mark partial so any completed units remain visible
        q.set_paper_status(upc, "partial")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Phase A — Pre-generation (serial)
# ─────────────────────────────────────────────────────────────────────────────

async def _phase_a_pre_generation(upc: str, cost: CostTracker) -> None:
    """Agents 1 → 4. Serial. Populates the database so Phase B can run in parallel."""

    # ── Agent 1: Decoder ─────────────────────────────────────────────────────
    if not q.get_paper(upc):
        log.info("[Agent 1] Decoding UPC %s", upc)
        paper_meta = await decoder.run(upc)
        q.upsert_paper(upc, paper_meta)
    else:
        log.info("[Agent 1] Skipped — paper row already exists")

    paper = q.get_paper(upc)
    if not paper:
        raise _PipelineHaltError(f"UPC {upc} not found in registry after decoder ran.")

    # ── Agent 2: Researcher ───────────────────────────────────────────────────
    if not q.paper_has_syllabus(upc):
        log.info("[Agent 2] Extracting syllabus for %s", upc)
        syllabus_json, raw_pyq_list = await researcher.run(upc, paper, cost)

        # ── Agent 2B: Researcher Verifier ─────────────────────────────────────
        log.info("[Agent 2B] Verifying syllabus extraction")
        for attempt in range(1, 3):
            verified = await researcher_verifier.run(upc, syllabus_json, cost)
            if verified:
                break
            log.warning("[Agent 2B] Verification failed (attempt %d/2)", attempt)
            if attempt == 2:
                raise _PipelineHaltError("Syllabus verification failed after 2 retries.")
            syllabus_json, raw_pyq_list = await researcher.run(upc, paper, cost)

        # Seed units and topics from syllabus
        _seed_units_and_topics(upc, syllabus_json)

        # ── Agent 2C: PYQ Normaliser ──────────────────────────────────────────
        if raw_pyq_list:
            log.info("[Agent 2C] Normalising %d PYQ paper(s)", len(raw_pyq_list))
            for raw_pyq in raw_pyq_list:
                for attempt in range(1, 3):
                    normalised = await pyq_normaliser.run(raw_pyq, upc, cost)
                    if normalised:
                        # Store normalised PYQ attached to papers row
                        _append_normalised_pyq(upc, normalised)
                        break
                    log.warning("[Agent 2C] Normalisation failed (attempt %d/2)", attempt)
        else:
            log.info("[Agent 2C] No PYQ papers found — continuing syllabus-based")

    else:
        log.info("[Agent 2] Skipped — syllabus already in DB")

    # ── Agent 3: Paper DNA ────────────────────────────────────────────────────
    if not q.paper_has_dna(upc):
        log.info("[Agent 3] Generating Paper DNA for %s", upc)
        dna_blob = await _run_paper_dna(upc, cost)
        q.set_paper_dna(upc, dna_blob)
    else:
        log.info("[Agent 3] Skipped — paper_dna already populated")

    # ── Agent 4: Mental Model Mapper ──────────────────────────────────────────
    if not q.units_have_mapper_data(upc):
        log.info("[Agent 4] Running Mental Model Mapper for %s", upc)
        await _run_mapper(upc, cost)
    else:
        log.info("[Agent 4] Skipped — mapper data already present")


def _seed_units_and_topics(upc: str, syllabus: dict) -> None:
    """Create unit + topic rows from the Researcher's extracted syllabus JSON."""
    existing_units = {u["unit_number"]: u for u in q.get_units_for_paper(upc)}

    for unit_data in syllabus.get("units", []):
        unit_num = unit_data["unit_number"]
        if unit_num not in existing_units:
            unit_row = q.create_unit(
                upc=upc,
                unit_number=unit_num,
                unit_name=unit_data["unit_name"],
                estimated_study_hours=unit_data.get("hours"),
            )
            unit_id = unit_row["id"]
        else:
            unit_id = existing_units[unit_num]["id"]

        # Create topic rows (topic_number = position in syllabus list)
        existing_topics = {t["topic_name"] for t in q.get_topics_for_unit(unit_id)}
        for idx, topic_name in enumerate(unit_data.get("topics", []), start=1):
            if topic_name not in existing_topics:
                q.create_topic(unit_id=unit_id, upc=upc,
                               topic_name=topic_name, topic_number=idx)


def _append_normalised_pyq(upc: str, normalised: dict) -> None:
    """Append one normalised PYQ JSON blob to papers.paper_dna (pre-DNA slot)."""
    paper = q.get_paper(upc)
    existing = paper.get("paper_dna") or {}
    raw_pyqs = existing.get("_raw_normalised_pyqs", [])
    raw_pyqs.append(normalised)
    existing["_raw_normalised_pyqs"] = raw_pyqs
    db.table("papers").update({"paper_dna": existing}).eq("upc", upc).execute()


async def _run_paper_dna(upc: str, cost: CostTracker) -> dict:
    """
    Agent 3 — four DNA analyses, assembled into one blob.
    Structural DNA is a mechanical extraction (no AI call).
    Topic + Language + Combination DNA use Gemini 2.0 Flash.
    """
    paper = q.get_paper(upc)
    raw_pyqs = (paper.get("paper_dna") or {}).get("_raw_normalised_pyqs", [])

    # Structural DNA — rule-based, no AI
    struct = structural_dna.run(raw_pyqs)

    if raw_pyqs:
        # Topic DNA + Language DNA (one Flash call — returns both arrays)
        for attempt in range(1, 3):
            async with _PRO_SEM:
                topic_lang = await topic_dna.run(raw_pyqs, upc, cost)
            if topic_lang:
                break
            if attempt == 2:
                log.warning("[Agent 3] Topic/Language DNA failed — using empty")
                topic_lang = {"topic_dna": [], "language_dna": []}

        # Combination DNA (second Flash call)
        for attempt in range(1, 3):
            async with _PRO_SEM:
                combo = await combination_dna.run(raw_pyqs, upc, cost)
            if combo:
                break
            if attempt == 2:
                log.warning("[Agent 3] Combination DNA failed — using empty")
                combo = {"combination_dna": []}
    else:
        topic_lang = {"topic_dna": [], "language_dna": []}
        combo = {"combination_dna": []}

    return {
        "structural_dna": struct,
        "topic_dna": topic_lang.get("topic_dna", []),
        "language_dna": topic_lang.get("language_dna", []),
        "combination_dna": combo.get("combination_dna", []),
    }


async def _run_mapper(upc: str, cost: CostTracker) -> None:
    """
    Agent 4 — Mental Model Mapper.
    Writes prerequisite links, optimised topic_number sequence,
    split_generation flags, and concept bridges back to topic rows.
    """
    units = q.get_units_for_paper(upc)
    paper = q.get_paper(upc)
    syllabus_units = [
        {"unit_id": u["id"], "unit_number": u["unit_number"],
         "unit_name": u["unit_name"],
         "topics": [
             {"topic_id": t["id"], "topic_name": t["topic_name"],
              "topic_number": t["topic_number"]}
             for t in q.get_topics_for_unit(u["id"])
         ]}
        for u in units
    ]

    for attempt in range(1, 3):
        async with _PRO_SEM:
            mapper_output = await mapper.run(syllabus_units, paper, cost)
        if mapper_output:
            break
        if attempt == 2:
            log.warning("[Agent 4] Mapper failed after 2 retries — using syllabus order")
            return  # No parallel processing; Writer will run sequentially

    # Apply mapper output: update topic rows with new sequence + bridges
    for topic_update in mapper_output.get("topic_updates", []):
        tid = topic_update["topic_id"]
        update_payload: dict[str, Any] = {
            "topic_number": topic_update["optimised_sequence_number"],
            "split_generation": topic_update.get("split_generation", False),
        }
        db.table("topics").update(update_payload).eq("id", tid).execute()

        if topic_update.get("prerequisite_topic_id"):
            q.set_topic_prerequisite(
                tid,
                topic_update["prerequisite_topic_id"],
                topic_update.get("prerequisite_bridge", ""),
            )
        if topic_update.get("connects_to_topic_id"):
            q.set_topic_connects_to(
                tid,
                topic_update["connects_to_topic_id"],
                topic_update.get("connects_to_reason", ""),
            )

    # Store independence map on the paper for Phase B to use
    independence_map = mapper_output.get("independence_map", {})
    paper_dna = q.get_paper(upc).get("paper_dna") or {}
    paper_dna["_independence_map"] = independence_map
    db.table("papers").update({"paper_dna": paper_dna}).eq("upc", upc).execute()


# ─────────────────────────────────────────────────────────────────────────────
# Phase B — Content generation (parallel across units and topics)
# ─────────────────────────────────────────────────────────────────────────────

async def _phase_b_content_generation(upc: str, cost: CostTracker) -> None:
    """
    Agents 5 → 9B.  Units without inter-unit dependencies fire in parallel.
    Within each unit, independent topics fire simultaneously.
    """
    paper = q.get_paper(upc)
    independence_map: dict = (paper.get("paper_dna") or {}).get("_independence_map", {})
    units = q.get_units_for_paper(upc)

    # Group units into dependency-ordered batches
    batches = _build_unit_batches(units, independence_map)

    for batch_num, unit_batch in enumerate(batches, start=1):
        log.info("[Phase B] Batch %d: %d unit(s) in parallel", batch_num, len(unit_batch))
        tasks = [
            _generate_unit(unit, upc, cost)
            for unit in unit_batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for unit, result in zip(unit_batch, results):
            if isinstance(result, Exception):
                log.error("Unit %s ('%s') failed: %s",
                          unit["id"], unit["unit_name"], result)
                # Mark failed but don't halt — other units remain accessible
                q.set_unit_status(unit["id"], "failed")


def _build_unit_batches(units: list[dict],
                         independence_map: dict) -> list[list[dict]]:
    """
    Return units split into sequential batches based on inter-unit dependencies.
    Units in the same batch can run in parallel.
    If no independence map (Mapper failed): return one batch per unit (fully sequential).
    """
    if not independence_map:
        return [[u] for u in units]

    independent_ids: set = set(independence_map.get("independent_unit_ids", []))
    dependent_ids: set = set(independence_map.get("dependent_unit_ids", []))

    independent = [u for u in units if u["id"] in independent_ids]
    dependent_ordered = [u for u in units if u["id"] in dependent_ids]
    # Units not in either map: treat as independent
    uncategorised = [u for u in units
                     if u["id"] not in independent_ids
                     and u["id"] not in dependent_ids]

    batches = []
    if independent or uncategorised:
        batches.append(independent + uncategorised)
    # Dependent units run one-by-one after independents complete
    for u in dependent_ordered:
        batches.append([u])

    return batches or [[u] for u in units]


async def _generate_unit(unit: dict, upc: str,
                          cost: CostTracker) -> None:
    """
    Drive one unit through Agents 5 → 9B.
    Resumes automatically if a unit previously failed.
    """
    unit_id = unit["id"]
    unit_name = unit["unit_name"]
    attempt = 0

    while attempt < MAX_UNIT_RESUME_ATTEMPTS:
        attempt += 1
        try:
            q.set_unit_status(unit_id, "generating")
            await _write_unit_topics(unit, upc, cost)
            q.set_unit_status(unit_id, "verifying")
            await _verify_and_critique_unit(unit, upc, cost)
            q.set_unit_status(unit_id, "complete")
            log.info("[Unit] '%s' complete", unit_name)
            return
        except CostKillSwitchError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("[Unit] '%s' attempt %d/%d failed: %s",
                        unit_name, attempt, MAX_UNIT_RESUME_ATTEMPTS, exc)
            if attempt >= MAX_UNIT_RESUME_ATTEMPTS:
                raise

    raise RuntimeError(f"Unit '{unit_name}' exhausted {MAX_UNIT_RESUME_ATTEMPTS} attempts")


async def _write_unit_topics(unit: dict, upc: str,
                              cost: CostTracker) -> None:
    """Agent 5 — fire Writer for every incomplete topic in this unit (parallel where independent)."""
    unit_id = unit["id"]
    topics = q.get_topics_for_unit(unit_id)
    paper = q.get_paper(upc)

    # Build dependency-aware topic batches (same logic as units)
    paper_dna = paper.get("paper_dna") or {}
    independence_map = paper_dna.get("_independence_map", {})
    # Mapper stores independence_map as a list of batch objects — normalise to dict
    if isinstance(independence_map, list):
        independence_map = {}
    independent_topic_ids: set = set(
        independence_map.get("independent_topic_ids", {}).get(unit_id, [])
    )

    pending = [t for t in topics if not q.topic_has_content(t["id"])]

    # Partition: independent topics run concurrently; dependent topics run after
    parallel_topics = [t for t in pending
                       if t["id"] in independent_topic_ids]
    sequential_topics = [t for t in pending
                         if t["id"] not in independent_topic_ids]

    if parallel_topics:
        await asyncio.gather(*[
            _write_single_topic(t, paper, cost) for t in parallel_topics
        ])
    for t in sequential_topics:
        await _write_single_topic(t, paper, cost)


async def _write_single_topic(topic: dict, paper: dict,
                               cost: CostTracker) -> None:
    """Agent 5 for one topic, with up to MAX_WRITER_RETRIES retries."""
    topic_id = topic["id"]
    topic_name = topic["topic_name"]
    q.set_topic_status(topic_id, "generating")

    for attempt in range(1, MAX_WRITER_RETRIES + 1):
        try:
            async with _FLASH_SEM:
                output = await writer.run(topic, paper, cost,
                                          split_mode=None if not topic.get("split_generation")
                                          else "content")

            if topic.get("split_generation"):
                # Second call for examples
                async with _FLASH_SEM:
                    examples_output = await writer.run(
                        topic, paper, cost, split_mode="examples"
                    )
                output = {**output, **examples_output}

            q.save_topic_content(topic_id, output)
            log.debug("[Writer] '%s' done (attempt %d)", topic_name, attempt)
            return

        except Exception as exc:  # noqa: BLE001
            log.warning("[Writer] '%s' attempt %d/%d: %s",
                        topic_name, attempt, MAX_WRITER_RETRIES, exc)
            if attempt == MAX_WRITER_RETRIES:
                q.set_topic_status(topic_id, "failed")
                raise

    # pragma: no cover


async def _verify_and_critique_unit(unit: dict, upc: str,
                                    cost: CostTracker) -> None:
    """Agents 6, 7, 8, 9, 9B — run on the completed unit."""
    unit_id = unit["id"]
    paper = q.get_paper(upc)
    topics = q.get_topics_for_unit(unit_id)
    complete_topics = [t for t in topics if t.get("definition")]

    # ── Agent 6: Coverage Checker (per unit, fast, Groq) ─────────────────────
    try:
        async with _GROQ_SEM:
            coverage_flags = await coverage_checker.run(unit, complete_topics, paper, cost)
        log.debug("[Agent 6] Coverage check complete for unit '%s'", unit["unit_name"])
    except Exception as exc:  # noqa: BLE001
        log.warning("[Agent 6] Coverage check skipped (Groq unavailable): %s", exc)
        coverage_flags = {}

    # ── Agents 7 + 8: Verify and Critique (parallel per topic) ───────────────
    await asyncio.gather(*[
        _verify_and_critique_topic(t, paper, coverage_flags, cost)
        for t in complete_topics
    ])


async def _verify_and_critique_topic(topic: dict, paper: dict,
                                     coverage_flags: dict,
                                     cost: CostTracker) -> None:
    """
    Agent 7 (Verifier) + Agent 8 (Critic) + Agent 9 (Rewriter) + Agent 9B
    for a single topic.  These run sequentially within the topic.
    """
    topic_id = topic["id"]
    topic_name = topic["topic_name"]

    # ── Agent 7: Verifier ─────────────────────────────────────────────────────
    if topic.get("priority") == "high":
        for attempt in range(1, MAX_VERIFIER_RETRIES + 1):
            try:
                async with _GROQ_SEM:
                    verify_result = await verifier.run(topic, paper, cost)
                if not verify_result.get("verified"):
                    log.info("[Agent 7] Verification flagged issues for '%s'", topic_name)
                break
            except Exception as exc:  # noqa: BLE001
                log.warning("[Agent 7] Failed for '%s' (attempt %d): %s",
                            topic_name, attempt, exc)
                verify_result = {"verified": False, "flagged_steps": []}
                if attempt == MAX_VERIFIER_RETRIES:
                    break
    else:
        verify_result = {"verified": None, "flagged_steps": []}

    # ── Agent 8: Critic ───────────────────────────────────────────────────────
    diff = None
    for attempt in range(1, MAX_CRITIC_RETRIES + 1):
        try:
            async with _FLASH_SEM:
                diff = await critic.run(topic, paper, verify_result, coverage_flags, cost)
            if diff:
                break
        except Exception as exc:  # noqa: BLE001
            log.warning("[Agent 8] Critic failed for '%s' (attempt %d): %s",
                        topic_name, attempt, exc)
            if attempt == MAX_CRITIC_RETRIES:
                log.warning("[Agent 8] Critic exhausted — topic proceeds uncorrected: %s",
                            topic_name)
                return

    if not diff or not diff.get("corrections"):
        log.debug("[Agent 8] No corrections needed for '%s'", topic_name)
        return

    # ── Agent 9: Rewriter ─────────────────────────────────────────────────────
    try:
        async with _FLASH_SEM:
            patched = await rewriter.run(topic, diff, paper, cost)

        # ── Agent 9B: Micro-validator ─────────────────────────────────────────
        for mv_attempt in range(1, 3):
            async with _GROQ_SEM:
                mv_result = await micro_validator.run(topic, patched, diff, cost)
            if mv_result.get("passed"):
                q.save_topic_content(topic_id, patched)
                log.debug("[Agent 9] Rewrite validated for '%s'", topic_name)
                return
            if mv_attempt == 2:
                log.warning("[Agent 9B] Micro-validation failed twice for '%s' — "
                            "retaining pre-rewrite value", topic_name)
                # Pre-rewrite value is already in DB; do not overwrite
                return

    except Exception as exc:  # noqa: BLE001
        log.warning("[Agent 9] Rewriter failed for '%s': %s", topic_name, exc)


# ─────────────────────────────────────────────────────────────────────────────
# Phase C — Coverage and patching (per unit → paper-level)
# ─────────────────────────────────────────────────────────────────────────────

async def _phase_c_coverage_and_patching(upc: str, cost: CostTracker) -> None:
    """Agents 10, 11, 11B, 12."""
    paper = q.get_paper(upc)
    units = q.get_units_for_paper(upc)

    # Agents 10 + 11 + 11B run per unit (serial — each unit's patch depends on examiner output)
    for unit in units:
        if unit["status"] != "complete":
            log.info("[Phase C] Skipping failed unit '%s'", unit["unit_name"])
            continue
        await _examine_and_patch_unit(unit, paper, cost)

    # ── Agent 12: Consistency Checker (paper-level, one Groq call) ────────────
    log.info("[Agent 12] Consistency check for %s", upc)
    try:
        all_topics = q.get_topics_for_paper(upc)
        async with _GROQ_SEM:
            violations = await consistency_checker.run(all_topics, paper, cost)

        await _apply_consistency_violations(violations, all_topics, paper, cost)

    except Exception as exc:  # noqa: BLE001
        log.warning("[Agent 12] Consistency check skipped (Groq unavailable): %s", exc)


async def _examine_and_patch_unit(unit: dict, paper: dict,
                                  cost: CostTracker) -> None:
    """Agents 10 → 11B for one unit."""
    unit_id = unit["id"]
    topics = q.get_topics_for_unit(unit_id)
    paper_dna = paper.get("paper_dna") or {}

    # ── Agent 10: Final Examiner ──────────────────────────────────────────────
    examiner_output = None
    for attempt in range(1, MAX_EXAMINER_RETRIES + 1):
        try:
            async with _FLASH_SEM:
                examiner_output = await final_examiner.run(
                    unit, topics, paper_dna, paper, cost
                )
            if examiner_output:
                break
        except Exception as exc:  # noqa: BLE001
            log.warning("[Agent 10] Final Examiner failed for unit '%s' (attempt %d): %s",
                        unit["unit_name"], attempt, exc)
            if attempt == MAX_EXAMINER_RETRIES:
                log.warning("[Agent 10] Proceeding with empty examiner output")
                examiner_output = {"uncovered_pyqs": [], "marks_incomplete_topics": []}

    uncovered = examiner_output.get("uncovered_pyqs", [])
    incomplete = examiner_output.get("marks_incomplete_topics", [])

    if not uncovered and not incomplete:
        log.debug("[Agent 10] Unit '%s' fully covered", unit["unit_name"])
        # Still need to generate conceptual summary
        await _generate_unit_summary(unit, topics, paper, cost)
        return

    log.info("[Agent 10] Unit '%s': %d uncovered PYQs, %d incomplete topics",
             unit["unit_name"], len(uncovered), len(incomplete))

    # ── Agent 11: Patcher ─────────────────────────────────────────────────────
    patch_output = None
    for attempt in range(1, MAX_PATCHER_RETRIES + 1):
        try:
            async with _FLASH_SEM:
                patch_output = await patcher.run(
                    unit, topics, examiner_output, paper, cost
                )
            if patch_output:
                break
        except Exception as exc:  # noqa: BLE001
            log.warning("[Agent 11] Patcher failed for unit '%s' (attempt %d): %s",
                        unit["unit_name"], attempt, exc)
            if attempt == MAX_PATCHER_RETRIES:
                log.warning("[Agent 11] Patch not applied for unit '%s'", unit["unit_name"])
                patch_output = {"topic_patches": [], "unit_patches": []}

    # Apply topic patches
    for tp in patch_output.get("topic_patches", []):
        q.save_topic_patch(tp["topic_id"], tp.get("patched_fields", {}))

    # Apply unit patches
    for up in patch_output.get("unit_patches", []):
        cs = up.get("conceptual_summary", {})
        if cs:
            q.save_unit_summary(
                up["unit_id"],
                conceptual_summary=cs,
                unit_closer={},  # closer generated in 11B
            )

    # ── Agent 11B: Post-Patch Regen ───────────────────────────────────────────
    patched_topic_ids = {tp["topic_id"] for tp in patch_output.get("topic_patches", [])}
    if patched_topic_ids:
        try:
            async with _FLASH_SEM:
                regen_output = await post_patch_regen.run(
                    list(patched_topic_ids), unit, paper, cost
                )
            for topic_regen in regen_output.get("topic_regens", []):
                q.save_topic_patch(topic_regen["topic_id"], topic_regen.get("fields", {}))
        except Exception as exc:  # noqa: BLE001
            log.warning("[Agent 11B] Post-patch regen failed: %s", exc)

    # Generate unit-level summary (conceptual_summary + unit_closer)
    await _generate_unit_summary(unit, q.get_topics_for_unit(unit_id), paper, cost)


async def _generate_unit_summary(unit: dict, topics: list[dict],
                                  paper: dict, cost: CostTracker) -> None:
    """
    Use Gemini Flash to build the conceptual_summary and unit_closer.
    This is a lightweight call — not a full agent, just a targeted prompt.
    """
    try:
        async with _FLASH_SEM:
            summary = await post_patch_regen.run_unit_summary(unit, topics, paper, cost)
        if summary:
            q.save_unit_summary(
                unit["id"],
                conceptual_summary=summary.get("conceptual_summary", {}),
                unit_closer=summary.get("unit_closer", {}),
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("[Summary] Could not generate unit summary for '%s': %s",
                    unit["unit_name"], exc)


async def _apply_consistency_violations(violations: dict,
                                        all_topics: list[dict],
                                        paper: dict,
                                        cost: CostTracker) -> None:
    """
    Agent 12 post-processing:
      - LaTeX violations → auto-patched by rule (no AI call)
      - Major violations → re-route affected topics back through Agent 8
    """
    topic_map = {t["id"]: t for t in all_topics}

    # Auto-patch LaTeX violations
    latex_violations = violations.get("latex_violations", [])
    for v in latex_violations:
        tid = v.get("topic_id")
        field = v.get("field")
        topic = topic_map.get(tid)
        if topic and field:
            _auto_fix_latex(tid, field, topic.get(field, ""))

    # Route major/critical violations back to Critic
    major_topic_ids: set[str] = set()
    for check in ("notation_violations", "definition_violations",
                  "pyq_year_violations", "priority_violations"):
        for v in violations.get(check, []):
            if v.get("severity") in ("critical", "major"):
                for tid in v.get("topic_ids", [v.get("topic_id")] if v.get("topic_id") else []):
                    major_topic_ids.add(tid)

    if major_topic_ids:
        log.info("[Agent 12] Re-routing %d topic(s) to Agent 8 for major violations",
                 len(major_topic_ids))
        await asyncio.gather(*[
            _verify_and_critique_topic(topic_map[tid], paper, {}, cost)
            for tid in major_topic_ids
            if tid in topic_map
        ])


def _auto_fix_latex(topic_id: str, field: str, value: Any) -> None:
    """Rule-based auto-correction of common unicode math symbols → LaTeX."""
    if not isinstance(value, str):
        return

    replacements = {
        "ε": r"\varepsilon", "λ": r"\lambda", "ω": r"\omega",
        "θ": r"\theta", "φ": r"\phi", "σ": r"\sigma",
        "μ": r"\mu", "π": r"\pi", "α": r"\alpha", "β": r"\beta",
        "γ": r"\gamma", "δ": r"\delta",
        "ℝ": r"\mathbb{R}", "ℕ": r"\mathbb{N}", "ℚ": r"\mathbb{Q}",
        "ℤ": r"\mathbb{Z}", "ℂ": r"\mathbb{C}",
    }
    fixed = value
    for unicode_char, latex in replacements.items():
        fixed = fixed.replace(unicode_char, f"${latex}$")

    if fixed != value:
        db.table("topics").update({field: fixed}).eq("id", topic_id).execute()
        log.debug("[Agent 12] Auto-fixed LaTeX in topic %s field '%s'", topic_id, field)


# ─────────────────────────────────────────────────────────────────────────────
# Internal exceptions
# ─────────────────────────────────────────────────────────────────────────────

class _PipelineHaltError(Exception):
    """Raised when the pipeline must stop cleanly (not a crash)."""


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="StudyAI pipeline runner")
    p.add_argument("upc", help="University Paper Code, e.g. BSCMT201")
    p.add_argument(
        "--force-rerun-from",
        type=int,
        default=None,
        metavar="AGENT_NUM",
        help="Clear and re-run from this agent number onwards (1-12)",
    )
    return p.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    args = _parse_args()
    t0 = time.perf_counter()
    asyncio.run(run_pipeline(args.upc, force_rerun_from=args.force_rerun_from))
    elapsed = time.perf_counter() - t0
    log.info("Total wall time: %.1fs", elapsed)