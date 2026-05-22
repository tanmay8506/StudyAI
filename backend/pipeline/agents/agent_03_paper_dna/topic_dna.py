"""
03_paper_dna/topic_dna.py
─────────────────────────
Agent 3 — Topic DNA + Language DNA component.

Uses Google Gemini 2.0 Flash for a dual-output call that produces
Topic DNA and Language DNA in a single API call separated by ---DNA_SPLIT---.
This minimises cost while keeping both analyses in the same context window.

Input:  List of normalised PYQ JSON objects + syllabus JSON
Output: (topic_dna list, language_dna list)

Both outputs conform to paper_dna_schema.json.

Called by: 03_paper_dna/combination_dna.py (which then calls this module,
           then saves the full DNA to Supabase)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

import google.generativeai as genai

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.0-flash"
DNA_SPLIT_DELIMITER = "---DNA_SPLIT---"
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    return path.read_text(encoding="utf-8")


def _get_client() -> genai.GenerativeModel:
    """Initialise and return a Gemini GenerativeModel client."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    return genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        generation_config=genai.types.GenerationConfig(
            temperature=0.0,
            max_output_tokens=4096,
        ),
    )


def extract_topic_and_language_dna(
    normalised_pyqs: list[dict[str, Any]],
    syllabus_json: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Extract Topic DNA and Language DNA from normalised PYQs.

    Performs two sequential Gemini calls:
      Call 1: Topic DNA + Language DNA (prompt: paper_dna_topic.txt, Call 1 section)
      Call 2: Topic DNA only — used to cross-check and merge Language DNA
              (uses paper_dna_language.txt for richer language extraction)

    The language_dna from Call 2 is used as the authoritative output because
    paper_dna_language.txt includes question_texts_verbatim which is needed
    downstream by the Critic.

    Args:
        normalised_pyqs: List of PYQ objects matching pyq_normalised_schema.json.
        syllabus_json:   Syllabus extraction matching syllabus_extraction_schema.json.

    Returns:
        (topic_dna, language_dna) — both as lists of dicts.

    Raises:
        ValueError: if Gemini returns malformed JSON after all retries.
        RuntimeError: if Gemini API call fails after all retries.
    """
    if not normalised_pyqs:
        logger.warning("No normalised PYQs for Topic/Language DNA. Returning empty.")
        return [], []

    client = _get_client()

    topic_dna_system = _load_prompt("paper_dna_topic.txt")
    language_dna_system = _load_prompt("paper_dna_language.txt")

    user_content = _build_user_message(normalised_pyqs, syllabus_json)

    # ── Call 1: Topic DNA + Language DNA (dual split output) ──────────────────
    logger.info("Topic DNA Call 1 — Topic + Language DNA extraction")
    topic_dna, language_dna_v1 = _run_dual_call(
        client=client,
        system_prompt=topic_dna_system,
        user_content=user_content,
    )

    # ── Call 2: Richer Language DNA extraction ────────────────────────────────
    logger.info("Topic DNA Call 2 — Rich Language DNA extraction")
    language_dna_v2 = _run_language_call(
        client=client,
        system_prompt=language_dna_system,
        user_content=user_content,
    )

    # Merge: language_dna_v2 is authoritative; v1 fills any gaps
    language_dna = _merge_language_dna(language_dna_v1, language_dna_v2)

    # Apply never_asked tags for topics on syllabus but not in any PYQ
    topic_dna = _tag_never_asked(topic_dna, syllabus_json)

    logger.info(
        "Topic DNA: %d topics | Language DNA: %d topics",
        len(topic_dna), len(language_dna)
    )

    return topic_dna, language_dna


# ──────────────────────────────────────────────────────────────────────────────
# Gemini call wrappers
# ──────────────────────────────────────────────────────────────────────────────

def _run_dual_call(
    client: genai.GenerativeModel,
    system_prompt: str,
    user_content: str,
) -> tuple[list[dict], list[dict]]:
    """
    Run the dual-output Gemini call (Topic DNA + Language DNA split by ---DNA_SPLIT---).
    Returns (topic_dna, language_dna).
    """
    # Gemini uses system_instruction at model level; we prepend it to the prompt
    full_prompt = f"{system_prompt}\n\n{user_content}"

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            response = client.generate_content(full_prompt)
            raw = response.text.strip()
            return _parse_dual_output(raw)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Topic DNA dual call parse error attempt %d: %s", attempt, e)
            if attempt > MAX_RETRIES:
                raise ValueError(f"Topic DNA failed after {MAX_RETRIES + 1} attempts: {e}") from e
            time.sleep(RETRY_DELAY_SECONDS)

        except Exception as e:
            logger.error("Gemini API error attempt %d: %s", attempt, e)
            if attempt > MAX_RETRIES:
                raise RuntimeError(f"Gemini API failed after {MAX_RETRIES + 1} attempts: {e}") from e
            time.sleep(RETRY_DELAY_SECONDS)

    return [], []


def _run_language_call(
    client: genai.GenerativeModel,
    system_prompt: str,
    user_content: str,
) -> list[dict]:
    """
    Run the dedicated Language DNA call (single JSON array output).
    """
    full_prompt = f"{system_prompt}\n\n{user_content}"

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            response = client.generate_content(full_prompt)
            raw = response.text.strip()
            return _parse_json_array(raw)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Language DNA call parse error attempt %d: %s", attempt, e)
            if attempt > MAX_RETRIES:
                logger.error("Language DNA failed all retries — returning empty list.")
                return []
            time.sleep(RETRY_DELAY_SECONDS)

        except Exception as e:
            logger.error("Gemini API error on Language DNA attempt %d: %s", attempt, e)
            if attempt > MAX_RETRIES:
                return []
            time.sleep(RETRY_DELAY_SECONDS)

    return []


# ──────────────────────────────────────────────────────────────────────────────
# Parsing helpers
# ──────────────────────────────────────────────────────────────────────────────

def _parse_dual_output(raw: str) -> tuple[list[dict], list[dict]]:
    """
    Parse the ---DNA_SPLIT--- delimited dual output.
    Returns (topic_dna, language_dna).
    """
    if DNA_SPLIT_DELIMITER not in raw:
        raise ValueError(
            f"DNA_SPLIT delimiter not found in Gemini output. "
            f"Raw output (first 300 chars): {raw[:300]}"
        )

    parts = raw.split(DNA_SPLIT_DELIMITER, 1)
    if len(parts) != 2:
        raise ValueError("Expected exactly 2 parts after splitting on ---DNA_SPLIT---")

    topic_raw, language_raw = parts[0].strip(), parts[1].strip()

    topic_dna = _parse_json_array(topic_raw)
    language_dna = _parse_json_array(language_raw)

    return topic_dna, language_dna


def _parse_json_array(raw: str) -> list[dict]:
    """Parse a JSON array from a string, stripping markdown fences if present."""
    clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE).strip()
    result = json.loads(clean)
    if not isinstance(result, list):
        raise ValueError(f"Expected JSON array, got {type(result).__name__}")
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Post-processing
# ──────────────────────────────────────────────────────────────────────────────

def _merge_language_dna(
    v1: list[dict[str, Any]],
    v2: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge two Language DNA lists. v2 is authoritative.
    For topics in v1 that are missing from v2, add them from v1.
    """
    v2_names = {item["topic_name"] for item in v2}
    merged = list(v2)
    for item in v1:
        if item["topic_name"] not in v2_names:
            merged.append(item)
            logger.debug("Language DNA merge: added '%s' from v1", item["topic_name"])
    return merged


def _tag_never_asked(
    topic_dna: list[dict[str, Any]],
    syllabus_json: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Add never_asked=True entries for syllabus topics not found in any PYQ.
    These are topics that need notes but have zero exam evidence.
    The Writer uses never_asked to produce one-line entries only.
    """
    existing_names = {item["topic_name"].lower() for item in topic_dna}
    never_asked_entries: list[dict[str, Any]] = []

    for unit in syllabus_json.get("units", []):
        for topic_name in unit.get("topics", []):
            if topic_name.lower() not in existing_names:
                never_asked_entries.append({
                    "topic_name":       topic_name,
                    "appearances":      [],
                    "total_appearances": 0,
                    "marks_trend":      "single_appearance",
                    "priority":         "never_asked",
                    "never_asked":      True,
                    "recency_weight":   1.0,
                })
                logger.debug("Tagged as never_asked: '%s'", topic_name)

    return topic_dna + never_asked_entries


def _build_user_message(
    normalised_pyqs: list[dict[str, Any]],
    syllabus_json: dict[str, Any],
) -> str:
    """Build the user message for Gemini DNA calls."""
    years = [pyq.get("year", "unknown") for pyq in normalised_pyqs]
    return (
        f"PAPER: {syllabus_json.get('paper_name', 'Unknown')} "
        f"(UPC: {syllabus_json.get('upc', 'Unknown')})\n"
        f"PYQ YEARS AVAILABLE: {', '.join(str(y) for y in years)}\n\n"
        f"SYLLABUS TOPICS:\n{_format_syllabus_topics(syllabus_json)}\n\n"
        f"NORMALISED PYQS:\n{json.dumps(normalised_pyqs, indent=2)}"
    )


def _format_syllabus_topics(syllabus_json: dict[str, Any]) -> str:
    """Format syllabus topics as a readable list for the Gemini prompt."""
    lines = []
    for unit in syllabus_json.get("units", []):
        lines.append(f"Unit {unit.get('unit_number')}: {unit.get('unit_name')}")
        for topic in unit.get("topics", []):
            lines.append(f"  - {topic}")
    return "\n".join(lines)

async def run(raw_pyqs: list[dict], upc: str, cost=None) -> dict:
    from database import queries as q
    import asyncio
    paper = q.get_paper(upc)
    syllabus_json = paper.get("syllabus") or {}
    topic_list, language_list = await asyncio.to_thread(extract_topic_and_language_dna, raw_pyqs, syllabus_json)
    return {"topic_dna": topic_list, "language_dna": language_list}
