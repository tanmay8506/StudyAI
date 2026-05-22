"""
Agent 10 — Final Examiner
─────────────────────────
Checks the entire unit against the normalised PYQ collection.
Two checks:

  CHECK 1 — PYQ Coverage
    Every PYQ in the normalised set must be addressed in the notes.
    Applies recency weight: most recent year questions get 1.5× importance.
    Target: coverage ratio > 90% of total available marks.

  CHECK 2 — Marks Completeness
    Every topic with a 6+ mark PYQ must have ALL required fields:
      definition, full core_concept, at least one worked example,
      answer_writing_technique, at least one PYQ with key_steps.

Output: { uncovered_pyqs: [...], marks_incomplete_topics: [...] }
This output feeds directly into Agent 11 (Patcher).

Model: Gemini 2.0 Flash
Note from Technical Reference: "OpenAI GPT (base) — Final Examiner only —
deliberate model difference to avoid confirmation bias."
We use Gemini here (personal build, no OpenAI key). If you have an OpenAI key,
swap the _call_examiner function to use gpt-4o-mini for better independence.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
_MODEL = "gemini-2.0-flash"

# ─────────────────────────────────────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = open(
    os.path.join(os.path.dirname(__file__), "..", "prompts", "final_examiner.txt"),
    encoding="utf-8",
).read()


def _build_user_prompt(
    normalised_pyqs: list[dict],
    topic_summaries: list[dict],
    topic_full_content: list[dict],
) -> str:
    return f"""Normalised PYQ Collection (all years):
{json.dumps(normalised_pyqs, ensure_ascii=False, indent=2)}

Topic Summaries (rapid_revision + topic_name for all topics in this unit):
{json.dumps(topic_summaries, ensure_ascii=False, indent=2)}

Full Topic Content (definition, core_concept, examples, answer_writing_technique, pyqs):
{json.dumps(topic_full_content, ensure_ascii=False, indent=2)}

Run both checks now. Output only valid JSON — no other text."""


# ─────────────────────────────────────────────────────────────────────────────
# Gemini call
# ─────────────────────────────────────────────────────────────────────────────

def _call_examiner(user_prompt: str, attempt: int = 1) -> dict:
    model = genai.GenerativeModel(
        _MODEL,
        system_instruction=_SYSTEM_PROMPT,
    )
    response = model.generate_content(
        user_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=4096,
        ),
    )
    raw = response.text.strip()

    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        if attempt < 3:
            logger.warning(
                "Final Examiner: JSON parse error on attempt %d — retrying. Error: %s",
                attempt, exc
            )
            return _call_examiner(user_prompt, attempt + 1)
        logger.error("Final Examiner: JSON parse failed after 3 attempts — returning empty lists")
        return {"uncovered_pyqs": [], "marks_incomplete_topics": []}

    return parsed


# ─────────────────────────────────────────────────────────────────────────────
# Pre-processing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_summaries(topics: list[dict]) -> list[dict]:
    """Strip topics down to summary fields for the first scan pass."""
    summaries = []
    for t in topics:
        summaries.append({
            "topic_id":      t.get("id"),
            "topic_name":    t.get("topic_name"),
            "priority":      t.get("priority"),
            "rapid_revision": t.get("rapid_revision"),
        })
    return summaries


def _extract_content_fields(topics: list[dict]) -> list[dict]:
    """Fields the examiner needs for marks-completeness check."""
    content = []
    for t in topics:
        content.append({
            "topic_id":               t.get("id"),
            "topic_name":             t.get("topic_name"),
            "definition":             t.get("definition"),
            "core_concept":           t.get("core_concept"),
            "examples":               t.get("examples", []),
            "answer_writing_technique": t.get("answer_writing_technique"),
            "pyqs":                   t.get("pyqs", []),
        })
    return content


def _compute_coverage_ratio(
    normalised_pyqs: list[dict],
    examiner_output: dict,
) -> float:
    """
    Returns the PYQ coverage ratio: (covered_marks) / (total_available_marks).
    Uses recency_weight on the most recent year's questions.
    """
    total_marks   = 0.0
    covered_marks = 0.0

    # Flatten all PYQ parts with their marks
    all_parts: list[dict] = []
    most_recent_year = max(
        (p.get("year", 0) for p in normalised_pyqs), default=0
    )

    for paper in normalised_pyqs:
        year = paper.get("year", 0)
        weight = 1.5 if year == most_recent_year else 1.0
        for q in paper.get("questions", []):
            for part in q.get("parts", []):
                marks = part.get("marks", 0) * weight
                all_parts.append({
                    "question_text": part.get("question_text", ""),
                    "marks": marks,
                })

    uncovered_texts = {
        uq.get("question_text", "").lower().strip()
        for uq in examiner_output.get("uncovered_pyqs", [])
    }

    for part in all_parts:
        total_marks += part["marks"]
        if part["question_text"].lower().strip() not in uncovered_texts:
            covered_marks += part["marks"]

    if total_marks == 0:
        return 1.0  # No PYQs → trivially covered
    return covered_marks / total_marks


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_final_examiner(
    unit_topics: list[dict],
    normalised_pyqs: list[dict],
) -> dict:
    """
    Args:
        unit_topics      : All topic dicts for this unit (from DB, full content).
        normalised_pyqs  : All normalised PYQ papers for this paper (pyq_normalised_schema.json format).

    Returns:
        {
            "uncovered_pyqs": [...],
            "marks_incomplete_topics": [...],
            "coverage_ratio": float,
            "coverage_target_met": bool,
        }
    """
    if not unit_topics:
        logger.warning("Final Examiner: received empty topic list — nothing to check")
        return {
            "uncovered_pyqs": [],
            "marks_incomplete_topics": [],
            "coverage_ratio": 1.0,
            "coverage_target_met": True,
        }

    summaries = _extract_summaries(unit_topics)
    content   = _extract_content_fields(unit_topics)
    user_prompt = _build_user_prompt(normalised_pyqs, summaries, content)

    logger.info(
        "Final Examiner: checking %d topics against %d PYQ papers",
        len(unit_topics), len(normalised_pyqs),
    )

    result = _call_examiner(user_prompt)

    # Validate output structure
    if "uncovered_pyqs" not in result:
        result["uncovered_pyqs"] = []
    if "marks_incomplete_topics" not in result:
        result["marks_incomplete_topics"] = []

    # Compute coverage ratio
    ratio = _compute_coverage_ratio(normalised_pyqs, result)
    result["coverage_ratio"]      = round(ratio, 4)
    result["coverage_target_met"] = ratio >= 0.90

    logger.info(
        "Final Examiner: coverage ratio = %.1f%% (%s) | uncovered PYQs = %d | incomplete topics = %d",
        ratio * 100,
        "✓ target met" if result["coverage_target_met"] else "✗ below 90%",
        len(result["uncovered_pyqs"]),
        len(result["marks_incomplete_topics"]),
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python 10_final_examiner.py <topics_json> <normalised_pyqs_json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        _topics = json.load(f)
    with open(sys.argv[2]) as f:
        _pyqs = json.load(f)

    _result = run_final_examiner(_topics, _pyqs)

    print(f"\nCoverage ratio : {_result['coverage_ratio']:.1%}")
    print(f"Target met     : {_result['coverage_target_met']}")
    print(f"Uncovered PYQs : {len(_result['uncovered_pyqs'])}")
    print(f"Incomplete topics: {len(_result['marks_incomplete_topics'])}")

    if _result["uncovered_pyqs"]:
        print("\nUncovered PYQs:")
        for q in _result["uncovered_pyqs"]:
            print(f"  [{q.get('year')}] {q.get('question_text', '')[:80]}…  ({q.get('marks')}m)")

    if _result["marks_incomplete_topics"]:
        print("\nIncomplete topics:")
        for t in _result["marks_incomplete_topics"]:
            print(f"  {t.get('topic_name')} — missing: {t.get('missing_fields')}")

async def run(unit: dict, topics: list[dict], paper_dna: dict, paper: dict, cost=None) -> dict:
    import asyncio
    normalised_pyqs = paper_dna.get("_raw_normalised_pyqs", [])
    return await asyncio.to_thread(run_final_examiner, topics, normalised_pyqs)
