"""
Agent 06 — Coverage Checker
Model: Groq (Llama 3)
Runs: Per unit, immediately after Writer completes all topics for that unit.
Purpose: Two-directional semantic check.
  Direction 1 — Syllabus → Notes: are any syllabus topics missing from the generated notes?
  Direction 2 — Notes → Syllabus: does any notes content go beyond the syllabus?
Output feeds into Agent 8 (Critic) as additional context flags.
This agent does NOT trigger rewrites — it flags. The Critic acts.
Retry: If Groq is unavailable, topic proceeds to Critic and this check is queued for retry.
"""

import json
import os
import logging
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 2048
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "coverage_checker.txt"


def _load_system_prompt() -> str:
    """Load the coverage checker system prompt from disk."""
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def _build_user_message(
    unit_name: str,
    unit_number: int,
    syllabus_topics: list[str],
    notes_summaries: list[dict],
    notes_definitions: list[dict],
) -> str:
    """
    Assemble the user message payload for the Groq call.

    Args:
        unit_name: Human-readable unit name (for context only).
        unit_number: Unit number within the paper.
        syllabus_topics: Raw list of topic strings from syllabus_extraction_schema.
        notes_summaries: List of { topic_id, topic_name, definition_one_line }.
        notes_definitions: List of { topic_id, definition, core_concept }.
    Returns:
        Formatted string to send as the user message.
    """
    return f"""UNIT {unit_number} — {unit_name}

SYLLABUS TOPICS:
{json.dumps(syllabus_topics, indent=2)}

NOTES SUMMARIES (rapid_revision.definition_one_line per topic):
{json.dumps(notes_summaries, indent=2)}

NOTES DEFINITIONS (definition + core_concept per topic):
{json.dumps(notes_definitions, indent=2)}

Run both coverage checks now. Output only valid JSON.
"""


def _validate_output(raw: str) -> dict:
    """
    Parse and structurally validate the Groq response.

    Expected shape:
        {
          "missing_topics": [{ "syllabus_entry": str, "closest_match": str | null }],
          "irrelevant_content": [{ "topic_id": str, "field": str, "excerpt": str }]
        }

    Raises:
        ValueError if the JSON is malformed or required keys are absent.
    """
    # Strip accidental markdown fences
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        clean = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Coverage Checker returned non-JSON: {exc}\nRaw:\n{raw[:400]}") from exc

    for key in ("missing_topics", "irrelevant_content"):
        if key not in data:
            raise ValueError(f"Coverage Checker output missing required key: '{key}'")
        if not isinstance(data[key], list):
            raise ValueError(f"Coverage Checker key '{key}' must be a list.")

    # Validate individual items lightly — full validation is cheap here
    for item in data["missing_topics"]:
        if "syllabus_entry" not in item:
            raise ValueError(f"missing_topics item missing 'syllabus_entry': {item}")

    for item in data["irrelevant_content"]:
        for field in ("topic_id", "field", "excerpt"):
            if field not in item:
                raise ValueError(f"irrelevant_content item missing '{field}': {item}")

    return data


def run_sync(
    unit_id: str,
    unit_name: str,
    unit_number: int,
    syllabus_topics: list[str],
    topics: list[dict],
) -> dict:
    """
    Execute the Coverage Checker for a single unit.

    Args:
        unit_id: UUID of the unit (used in logs only; not sent to model).
        unit_name: Human-readable unit name.
        unit_number: Unit number within the paper.
        syllabus_topics: List of topic strings from the extracted syllabus for this unit.
        topics: List of fully-generated topic dicts from the Writer.
                Each dict must contain at minimum:
                  id, topic_name, rapid_revision.definition_one_line,
                  definition, core_concept.

    Returns:
        dict with keys:
          "unit_id": str
          "missing_topics": list[dict]   — syllabus entries not covered in notes
          "irrelevant_content": list[dict] — notes content not traceable to syllabus
          "skipped": bool                — True if Groq was unavailable (soft failure)
          "error": str | None            — populated only if skipped is True
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    # Build structured summaries for the model — only what it needs, not full topic dicts
    notes_summaries = [
        {
            "topic_id": t["id"],
            "topic_name": t.get("topic_name", ""),
            "definition_one_line": (
                t.get("rapid_revision", {}).get("definition_one_line", "")
                if t.get("rapid_revision")
                else ""
            ),
        }
        for t in topics
    ]

    notes_definitions = [
        {
            "topic_id": t["id"],
            "definition": t.get("definition", ""),
            "core_concept": t.get("core_concept", ""),
        }
        for t in topics
    ]

    system_prompt = _load_system_prompt()
    user_message = _build_user_message(
        unit_name=unit_name,
        unit_number=unit_number,
        syllabus_topics=syllabus_topics,
        notes_summaries=notes_summaries,
        notes_definitions=notes_definitions,
    )

    logger.info(
        "Coverage Checker starting | unit_id=%s | unit=%d – %s | topics=%d | syllabus_entries=%d",
        unit_id, unit_number, unit_name, len(topics), len(syllabus_topics),
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.0,           # Deterministic — this is a mechanical check
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception as exc:
        # Soft failure — pipeline continues, check queued for retry in orchestrator
        logger.warning(
            "Coverage Checker skipped (Groq unavailable) | unit_id=%s | error=%s",
            unit_id, exc,
        )
        return {
            "unit_id": unit_id,
            "missing_topics": [],
            "irrelevant_content": [],
            "skipped": True,
            "error": str(exc),
        }

    raw_output = response.choices[0].message.content

    try:
        result = _validate_output(raw_output)
    except ValueError as exc:
        # Validation failure is a soft error — log and skip rather than crash the unit
        logger.error(
            "Coverage Checker validation failed | unit_id=%s | error=%s | raw=%s",
            unit_id, exc, raw_output[:200],
        )
        return {
            "unit_id": unit_id,
            "missing_topics": [],
            "irrelevant_content": [],
            "skipped": True,
            "error": str(exc),
        }

    missing_count = len(result["missing_topics"])
    irrelevant_count = len(result["irrelevant_content"])

    logger.info(
        "Coverage Checker complete | unit_id=%s | missing=%d | irrelevant=%d",
        unit_id, missing_count, irrelevant_count,
    )

    if missing_count > 0:
        for item in result["missing_topics"]:
            logger.warning(
                "MISSING COVERAGE | unit_id=%s | syllabus_entry='%s' | closest_match=%s",
                unit_id,
                item["syllabus_entry"],
                item.get("closest_match", "null"),
            )

    return {
        "unit_id": unit_id,
        "missing_topics": result["missing_topics"],
        "irrelevant_content": result["irrelevant_content"],
        "skipped": False,
        "error": None,
    }

async def run(unit: dict, complete_topics: list[dict], paper: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_sync, unit["id"], unit["unit_name"], unit["unit_number"], [t["topic_name"] for t in complete_topics], complete_topics)
