"""
04_mental_model_mapper.py
─────────────────────────
Agent 4 — Mental Model Mapper.

[TESTING MODE] Uses Groq (Llama 3.3-70b-versatile) instead of Gemini.
Switch back to Gemini for production by restoring _get_client() and
replacing _run_mapper_call() with the Gemini version.

Produces:
  1. dependency_graph      — prerequisite links for every topic
  2. optimised_sequence    — best study order per unit
  3. independence_map      — parallel processing batches
  4. concept_bridges       — one sentence per prerequisite link
  5. split_generation_flags — topics that need split Writer calls

Runs AFTER Paper DNA is complete. Requires:
  - syllabus_json (from Agent 2)
  - paper_dna (from Agent 3)

Max 2 retries on schema failure.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from groq import Groq

from utils.cycle_detector import (
    TopicNode,
    build_processing_batches,
    compute_dependency_depths,
    detect_and_resolve_cycles,
)

logger = logging.getLogger(__name__)

# ── Model config (Groq for testing; swap to Gemini for production) ────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _get_client() -> Groq:
    """Initialise and return a Groq client."""
    return Groq(api_key=os.environ["GROQ_API_KEY"])


# ──────────────────────────────────────────────────────────────────────────────
# Public interface
# ──────────────────────────────────────────────────────────────────────────────

def run_mental_model_mapper(
    upc: str,
    syllabus_json: dict[str, Any],
    paper_dna: dict[str, Any],
    supabase_client: Any,
) -> dict[str, Any]:
    """
    Run the full Mental Model Mapper for a paper.

    Args:
        upc:             Paper UPC identifier.
        syllabus_json:   Syllabus extraction (syllabus_extraction_schema.json).
        paper_dna:       Assembled paper DNA (paper_dna_schema.json).
        supabase_client: Initialised Supabase client.

    Returns:
        mapper_output dict with all five keys:
          dependency_graph, optimised_sequence, independence_map,
          concept_bridges, split_generation_flags, cycle_warnings.

    Raises:
        ValueError: if Gemini output fails schema validation after all retries.
        RuntimeError: if Gemini API fails after all retries.
    """
    logger.info("Mental Model Mapper starting for UPC: %s", upc)

    # ── Step 1: Run Gemini Mapper ─────────────────────────────────────────────
    mapper_output = _run_mapper_call(syllabus_json, paper_dna)

    # ── Step 2: Run cycle detection on Gemini's dependency graph ─────────────
    mapper_output = _apply_cycle_detection(mapper_output, syllabus_json)

    # ── Step 3: Recompute independence_map from safe graph ────────────────────
    mapper_output["independence_map"] = _rebuild_independence_map(
        mapper_output["dependency_graph"]
    )

    # ── Step 4: Write mapper output to Supabase topics table ──────────────────
    _write_mapper_to_db(upc, mapper_output, supabase_client)

    logger.info("Mental Model Mapper complete for UPC: %s", upc)
    return mapper_output


# ──────────────────────────────────────────────────────────────────────────────
# Gemini call
# ──────────────────────────────────────────────────────────────────────────────

def _run_mapper_call(
    syllabus_json: dict[str, Any],
    paper_dna: dict[str, Any],
) -> dict[str, Any]:
    """
    Call Groq (Llama 3.3-70b-versatile) with the mapper prompt.
    Retries up to MAX_RETRIES on parse/validation failure.
    """
    client = _get_client()
    system_prompt = _load_prompt("mapper.txt")
    user_content = _build_mapper_user_message(syllabus_json, paper_dna)

    for attempt in range(1, MAX_RETRIES + 2):
        logger.info("Mapper Groq call — attempt %d/%d", attempt, MAX_RETRIES + 1)
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.0,
                max_tokens=8192,
            )
            raw = response.choices[0].message.content.strip()
            result = _parse_mapper_output(raw)
            _validate_mapper_output(result, syllabus_json)
            logger.info("Mapper call succeeded on attempt %d.", attempt)
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Mapper parse/validation error attempt %d: %s", attempt, e)
            if attempt > MAX_RETRIES:
                raise ValueError(
                    f"Mapper failed to produce valid output after {MAX_RETRIES + 1} attempts: {e}"
                ) from e
            time.sleep(RETRY_DELAY_SECONDS)

        except Exception as e:
            logger.error("Groq API error attempt %d: %s", attempt, e)
            if attempt > MAX_RETRIES:
                raise RuntimeError(
                    f"Groq API failed for Mapper after {MAX_RETRIES + 1} attempts: {e}"
                ) from e
            time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError("Mapper exhausted retries — this should be unreachable.")


def _build_mapper_user_message(
    syllabus_json: dict[str, Any],
    paper_dna: dict[str, Any],
) -> str:
    """Assemble the Mapper user message from syllabus + paper DNA."""
    topic_dna_summary = _format_topic_dna_summary(paper_dna.get("topic_dna", []))
    combination_summary = _format_combination_summary(paper_dna.get("combination_dna", []))

    return (
        f"PAPER: {syllabus_json.get('paper_name', 'Unknown')} "
        f"(UPC: {syllabus_json.get('upc', 'Unknown')})\n"
        f"PAPER TYPE: {syllabus_json.get('paper_type', 'theory')}\n\n"
        f"COMPLETE SYLLABUS:\n{json.dumps(syllabus_json, indent=2)}\n\n"
        f"TOPIC DNA (priority + appearance data):\n{topic_dna_summary}\n\n"
        f"COMBINATION DNA (topics always asked together):\n{combination_summary}\n\n"
        f"Produce the full Mapper JSON output now. No prose. Valid JSON only."
    )


def _format_topic_dna_summary(topic_dna: list[dict]) -> str:
    lines = []
    for item in topic_dna:
        priority = item.get("priority", "unknown")
        appearances = item.get("total_appearances", 0)
        never = item.get("never_asked", False)
        lines.append(
            f"  {item.get('topic_name', '?')} | priority={priority} "
            f"| appearances={appearances} | never_asked={never}"
        )
    return "\n".join(lines) if lines else "  (no topic DNA available)"


def _format_combination_summary(combination_dna: list[dict]) -> str:
    lines = []
    for item in combination_dna:
        always_with = item.get("always_asked_with", [])
        if always_with:
            lines.append(
                f"  {item.get('topic_name', '?')} → always with: {', '.join(always_with)}"
            )
    return "\n".join(lines) if lines else "  (no combination patterns detected)"


# ──────────────────────────────────────────────────────────────────────────────
# Output parsing and validation
# ──────────────────────────────────────────────────────────────────────────────

def _parse_mapper_output(raw: str) -> dict[str, Any]:
    """Parse Gemini's JSON output for the Mapper."""
    clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE).strip()
    return json.loads(clean)


def _validate_mapper_output(
    output: dict[str, Any],
    syllabus_json: dict[str, Any],
) -> None:
    """
    Validate mapper output has required keys and all syllabus topics are covered.
    Raises ValueError on critical missing data.
    """
    required_keys = [
        "dependency_graph", "optimised_sequence",
        "independence_map", "concept_bridges", "split_generation_flags",
    ]
    for key in required_keys:
        if key not in output:
            raise ValueError(f"Mapper output missing required key: '{key}'")

    # Ensure optimised_sequence covers every unit in the syllabus
    syllabus_unit_numbers = {u["unit_number"] for u in syllabus_json.get("units", [])}
    sequence_unit_numbers = {s["unit_number"] for s in output.get("optimised_sequence", [])}
    missing_units = syllabus_unit_numbers - sequence_unit_numbers
    if missing_units:
        raise ValueError(
            f"Mapper optimised_sequence missing units: {sorted(missing_units)}"
        )

    # Set default for cycle_warnings if not present
    output.setdefault("cycle_warnings", [])


# ──────────────────────────────────────────────────────────────────────────────
# Cycle detection integration
# ──────────────────────────────────────────────────────────────────────────────

def _apply_cycle_detection(
    mapper_output: dict[str, Any],
    syllabus_json: dict[str, Any],
) -> dict[str, Any]:
    """
    Run cycle_detector on the dependency_graph Gemini produced.
    If cycles are found, patch the graph and inject cycle_warnings.
    """
    dep_graph = mapper_output.get("dependency_graph", [])

    topic_nodes = [
        TopicNode(
            name=item.get("topic_name", ""),
            prerequisite=item.get("prerequisite_topic_name"),
        )
        for item in dep_graph
    ]

    report = detect_and_resolve_cycles(topic_nodes)

    if report.has_cycles:
        logger.warning(
            "Cycle detector found %d cycle(s) in Mapper output. Resolving.",
            len(report.warnings)
        )
        # Patch the dependency_graph with the safe (acyclic) graph
        safe_prereqs = {node.name: node.prerequisite for node in report.safe_graph}
        for item in dep_graph:
            original_prereq = item.get("prerequisite_topic_name")
            safe_prereq = safe_prereqs.get(item["topic_name"])
            if original_prereq != safe_prereq:
                logger.info(
                    "Cycle resolved: '%s' prerequisite changed from '%s' to None",
                    item["topic_name"], original_prereq
                )
                item["prerequisite_topic_name"] = safe_prereq

        # Recompute dependency depths on safe graph
        depths = compute_dependency_depths(report.safe_graph)
        for item in dep_graph:
            item["dependency_depth"] = depths.get(item["topic_name"], 0)

        # Add cycle warnings to output
        cycle_warnings = [
            {
                "cycle_description": f"Cycle: {' → '.join(w.cycle_topics)}",
                "entry_point": w.entry_point,
                "resolution": w.resolution_note,
            }
            for w in report.warnings
        ]
        mapper_output["cycle_warnings"] = cycle_warnings

        # Inject mutual_dependency note into concept_bridges for affected topics
        cycle_entry_names = {w.entry_point for w in report.warnings}
        existing_bridge_names = {
            b["dependent_topic"] for b in mapper_output.get("concept_bridges", [])
        }
        for warning in report.warnings:
            if warning.entry_point not in existing_bridge_names:
                mapper_output["concept_bridges"].append({
                    "dependent_topic":    warning.entry_point,
                    "prerequisite_topic": warning.removed_edge_to,
                    "which_concept":      "mutual dependency — see cycle resolution",
                    "why_needed":         "topics are mutually dependent",
                    "bridge_sentence":    warning.resolution_note,
                })

    else:
        logger.info("No cycles detected in Mapper output.")

    mapper_output["dependency_graph"] = dep_graph
    return mapper_output


def _rebuild_independence_map(
    dep_graph: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Recompute the independence_map (processing batches) from the safe dependency graph.
    Replaces whatever Gemini generated with arithmetically correct batches.
    """
    topic_nodes = [
        TopicNode(
            name=item.get("topic_name", ""),
            prerequisite=item.get("prerequisite_topic_name"),
        )
        for item in dep_graph
    ]
    batches = build_processing_batches(topic_nodes)

    # Build unit_number lookup from dep_graph
    unit_lookup = {
        item["topic_name"]: item.get("unit_number", 0)
        for item in dep_graph
    }

    return [
        {
            "batch_number": batch_num,
            "topics": [
                {
                    "topic_name":          topic_name,
                    "unit_number":         unit_lookup.get(topic_name, 0),
                    "safe_to_parallelize": True,
                }
                for topic_name in batch
            ],
        }
        for batch_num, batch in enumerate(batches)
    ]


# ──────────────────────────────────────────────────────────────────────────────
# Supabase writes
# ──────────────────────────────────────────────────────────────────────────────

def _write_mapper_to_db(
    upc: str,
    mapper_output: dict[str, Any],
    supabase_client: Any,
) -> None:
    """
    Write Mapper results to the topics table.

    For each topic in the dependency_graph:
      - prerequisite_bridge  ← concept_bridge.bridge_sentence for this topic
      - split_generation     ← True if in split_generation_flags

    Note: prerequisite_topic_id (UUID FK) is resolved by the orchestrator
    after all topic rows exist. Here we write the name-based bridge only.
    """
    # Build lookup: topic_name → concept_bridge sentence
    bridge_lookup: dict[str, str] = {}
    for bridge in mapper_output.get("concept_bridges", []):
        dep_topic = bridge.get("dependent_topic", "")
        sentence = bridge.get("bridge_sentence", "")
        if dep_topic and sentence:
            bridge_lookup[dep_topic] = sentence

    # Build lookup: topic_name → split_generation flag
    split_lookup: set[str] = {
        item["topic_name"]
        for item in mapper_output.get("split_generation_flags", [])
    }

    # Build update payload per topic
    for item in mapper_output.get("dependency_graph", []):
        topic_name = item.get("topic_name", "")
        if not topic_name:
            continue

        update_data: dict[str, Any] = {}
        if topic_name in bridge_lookup:
            update_data["prerequisite_bridge"] = bridge_lookup[topic_name]
        if topic_name in split_lookup:
            update_data["split_generation"] = True

        if update_data:
            result = (
                supabase_client
                .table("topics")
                .update(update_data)
                .eq("upc", upc)
                .eq("topic_name", topic_name)
                .execute()
            )
            if not result.data:
                logger.warning(
                    "Mapper DB write: no rows updated for topic '%s' (UPC: %s). "
                    "Topic may not exist yet — orchestrator will retry.",
                    topic_name, upc
                )

    logger.info("Mapper results written to topics table for UPC: %s", upc)

async def run(syllabus_units: list[dict], paper: dict, cost=None) -> dict:
    from database import queries as q
    import asyncio
    upc = paper["upc"]
    syllabus_json = paper.get("syllabus", {"units": syllabus_units})
    paper_dna = paper.get("paper_dna", {})
    return await asyncio.to_thread(run_mental_model_mapper, upc, syllabus_json, paper_dna, q.db)
