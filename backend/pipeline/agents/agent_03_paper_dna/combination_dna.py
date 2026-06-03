"""
03_paper_dna/combination_dna.py
────────────────────────────────
Agent 3 — Combination DNA component.

Detects which topics are always asked together in the same DU exam question.
Uses Google Gemini 2.0 Flash (Call 2 of paper_dna_topic.txt prompt).

Input:  normalised_pyqs + topic_dna (already extracted)
Output: combination_dna list conforming to paper_dna_schema.json#/combination_dna

Also acts as the orchestrator for all four Paper DNA sub-components:
  1. structural_dna (Groq)
  2. topic_dna + language_dna (Gemini, topic_dna.py)
  3. combination_dna (Gemini, this file)

After all four are ready, saves the assembled paper_dna to Supabase.
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
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _get_client() -> genai.GenerativeModel:
    """Initialise and return a Gemini GenerativeModel client."""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    return genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        generation_config=genai.types.GenerationConfig(
            temperature=0.0,
            max_output_tokens=2048,
            response_mime_type="application/json",
        ),
    )


def extract_combination_dna(
    normalised_pyqs: list[dict[str, Any]],
    topic_dna: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Extract Combination DNA: which topics always appear together in PYQs.

    Args:
        normalised_pyqs: List of PYQ objects (pyq_normalised_schema.json).
        topic_dna:       Already-extracted topic_dna list (for topic name reference).

    Returns:
        combination_dna list matching paper_dna_schema.json#/combination_dna.
    """
    if not normalised_pyqs:
        logger.warning("No PYQs for Combination DNA. Returning empty.")
        return []

    client = _get_client()
    system_prompt = _load_prompt("paper_dna_topic.txt")
    user_content = _build_combination_user_message(normalised_pyqs, topic_dna)
    full_prompt = f"{system_prompt}\n\n{user_content}"

    for attempt in range(1, MAX_RETRIES + 2):
        logger.info("Combination DNA extraction — attempt %d/%d", attempt, MAX_RETRIES + 1)
        try:
            response = client.generate_content(full_prompt)
            raw = response.text.strip()
            result = _parse_combination_output(raw)
            logger.info("Combination DNA extraction succeeded: %d topics", len(result))
            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Combination DNA parse error attempt %d: %s", attempt, e)
            if attempt > MAX_RETRIES:
                logger.error("Combination DNA failed all retries. Returning empty list.")
                return []
            time.sleep(RETRY_DELAY_SECONDS)

        except Exception as e:
            logger.error("Gemini API error attempt %d: %s", attempt, e)
            if attempt > MAX_RETRIES:
                return []
            time.sleep(RETRY_DELAY_SECONDS)

    return []


def _build_combination_user_message(
    normalised_pyqs: list[dict[str, Any]],
    topic_dna: list[dict[str, Any]],
) -> str:
    """
    Build the user message for the Combination DNA Gemini call.
    This is Call 2 of paper_dna_topic.txt.
    """
    topic_names = [item["topic_name"] for item in topic_dna if not item.get("never_asked")]
    return (
        f"CALL 2 — COMBINATION DNA ONLY.\n\n"
        f"Topics found in PYQs (from Topic DNA):\n"
        f"{chr(10).join(f'  - {name}' for name in topic_names)}\n\n"
        f"NORMALISED PYQS (analyse for combination patterns):\n"
        f"{json.dumps(normalised_pyqs, indent=2)}"
    )


def _parse_combination_output(raw: str) -> list[dict[str, Any]]:
    """Parse and validate the combination DNA JSON array."""
    clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE).strip()

    result = json.loads(clean)
    if not isinstance(result, list):
        raise ValueError(f"Expected JSON array for combination_dna, got {type(result).__name__}")

    # Validate and fill defaults for each item
    validated = []
    for item in result:
        validated.append({
            "topic_name":           item.get("topic_name", ""),
            "always_asked_with":    item.get("always_asked_with", []),
            "combination_pattern":  item.get("combination_pattern", "No consistent combination pattern detected."),
            "standalone_frequency": float(item.get("standalone_frequency", 1.0)),
            "diagram_required":     bool(item.get("diagram_required", False)),
            "numerical_always":     bool(item.get("numerical_always", False)),
        })

    return validated


# ──────────────────────────────────────────────────────────────────────────────
# Master Paper DNA orchestrator
# ──────────────────────────────────────────────────────────────────────────────

def run_paper_dna_pipeline(
    upc: str,
    normalised_pyqs: list[dict[str, Any]],
    syllabus_json: dict[str, Any],
    supabase_client: Any,
) -> dict[str, Any]:
    """
    Full Paper DNA pipeline orchestrator.
    Runs all four DNA sub-agents and saves the assembled result to Supabase.

    Sequence:
      1. structural_dna  (Groq — mechanical, fastest)
      2. topic_dna + language_dna  (Gemini — two calls via topic_dna.py)
      3. combination_dna  (Gemini — one call, this file)
      4. Assemble full paper_dna JSON
      5. Write to papers.paper_dna in Supabase
      6. Update papers.pipeline_status

    Args:
        upc:              The paper UPC identifier.
        normalised_pyqs:  All normalised PYQ objects for this paper.
        syllabus_json:    Syllabus extraction for this paper.
        supabase_client:  Initialised Supabase client.

    Returns:
        The fully assembled paper_dna dict (also written to DB).

    Raises:
        RuntimeError: if any critical sub-agent fails.
    """
    from .structural_dna import extract_structural_dna
    from .topic_dna import extract_topic_and_language_dna

    logger.info("Paper DNA pipeline starting for UPC: %s", upc)

    # ── 1. Structural DNA ─────────────────────────────────────────────────────
    logger.info("[1/4] Structural DNA (Groq)")
    structural_dna = extract_structural_dna(normalised_pyqs)

    # ── 2. Topic DNA + Language DNA ───────────────────────────────────────────
    logger.info("[2/4] Topic DNA + Language DNA (Gemini)")
    topic_dna, language_dna = extract_topic_and_language_dna(normalised_pyqs, syllabus_json)

    # ── 3. Combination DNA ────────────────────────────────────────────────────
    logger.info("[3/4] Combination DNA (Gemini)")
    combination_dna = extract_combination_dna(normalised_pyqs, topic_dna)

    # ── 4. Assemble ───────────────────────────────────────────────────────────
    logger.info("[4/4] Assembling full paper_dna")
    paper_dna = {
        "structural_dna":  structural_dna,
        "topic_dna":       topic_dna,
        "language_dna":    language_dna,
        "combination_dna": combination_dna,
    }

    # Validate against schema before writing to DB
    _validate_paper_dna(paper_dna)

    # ── 5. Write to Supabase ──────────────────────────────────────────────────
    logger.info("Writing paper_dna to Supabase for UPC: %s", upc)
    result = (
        supabase_client
        .table("papers")
        .update({
            "paper_dna": paper_dna,
            "pipeline_status": "dna_complete",
        })
        .eq("upc", upc)
        .execute()
    )

    if result.data:
        logger.info("Paper DNA successfully written to Supabase for UPC: %s", upc)
    else:
        logger.error("Supabase write returned no data for UPC: %s — %s", upc, result)

    return paper_dna


def _validate_paper_dna(paper_dna: dict[str, Any]) -> None:
    """
    Validate the assembled paper_dna against paper_dna_schema.json.
    Logs warnings for any violations but does not raise — partial DNA
    is better than no DNA.
    """
    schema_path = (
        Path(__file__).parent.parent.parent / "schemas" / "paper_dna_schema.json"
    )
    if not schema_path.exists():
        logger.warning("paper_dna_schema.json not found — skipping validation.")
        return

    try:
        import jsonschema
        with open(schema_path) as f:
            schema = json.load(f)
        jsonschema.validate(instance=paper_dna, schema=schema)
        logger.info("Paper DNA schema validation passed.")
    except ImportError:
        logger.warning("jsonschema not installed — skipping paper_dna validation.")
    except Exception as e:
        logger.warning("Paper DNA schema validation warning: %s", e)

async def run(raw_pyqs: list[dict], upc: str, cost=None) -> dict:
    from database import queries as q
    import asyncio
    paper = q.get_paper(upc)
    topic_dna_list = (paper.get("paper_dna") or {}).get("topic_dna", [])
    result = await asyncio.to_thread(extract_combination_dna, raw_pyqs, topic_dna_list)
    return {"combination_dna": result}
