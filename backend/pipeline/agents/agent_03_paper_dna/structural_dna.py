"""
03_paper_dna/structural_dna.py
──────────────────────────────
Agent 3 — Structural DNA component.

Extracts the mechanical structure of a DU paper: total marks, sections,
question counts, attempt requirements. Uses Groq (Llama 3) — fast, cheap,
rule-based extraction that does not need Claude's reasoning capability.

Input:  List of normalised PYQ JSON objects (from pyq_normalised_schema.json)
Output: structural_dna dict conforming to paper_dna_schema.json#/structural_dna

Called by: 03_paper_dna/topic_dna.py (orchestrates all 4 DNA sub-agents)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from groq import Groq

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama3-70b-8192"
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 3

_SYSTEM_PROMPT = """You are a mechanical structure extractor for exam papers.
You receive normalised PYQ JSON for a DU B.Sc. NEP paper.

Extract the structural pattern of the exam paper and output ONLY valid JSON.
No prose. No markdown. No preamble.

Output schema:
{
  "total_marks": integer,
  "time_allowed_minutes": integer,
  "sections": [
    {
      "section_label": "string (e.g. 'Section A', 'Part I')",
      "marks_per_question": integer,
      "total_questions": integer,
      "attempt_count": integer,
      "compulsory": boolean
    }
  ],
  "question_distribution": [
    {
      "unit_number": integer,
      "appearances_across_years": integer,
      "avg_marks_per_year": number
    }
  ],
  "attempt_all": boolean,
  "attempt": integer
}

Rules:
- total_marks: sum marks from the most representative PYQ year available.
- time_allowed_minutes: extract from paper header if present; else null.
- sections: one entry per distinct section. If paper has no sections, one entry labelled "Main".
- attempt_count: how many questions the student must attempt in that section.
  If all questions are compulsory: attempt_count = total_questions, compulsory = true.
- question_distribution: aggregate across ALL provided PYQ years.
  appearances_across_years = how many times questions from that unit appeared across all years.
  avg_marks_per_year = average marks from that unit per PYQ year.
- attempt_all: true if student must attempt every question (no choice).
- attempt: total questions the student must attempt across the entire paper.
  If attempt_all = true: attempt = total questions in paper.

If any value cannot be determined from the data: use null. Do not guess.
"""


def extract_structural_dna(normalised_pyqs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Extract structural DNA from normalised PYQ JSON objects.

    Args:
        normalised_pyqs: List of PYQ objects matching pyq_normalised_schema.json.

    Returns:
        structural_dna dict matching paper_dna_schema.json#/structural_dna.

    Raises:
        ValueError: if Groq returns unparseable JSON after all retries.
        RuntimeError: if Groq API call fails after all retries.
    """
    if not normalised_pyqs:
        logger.warning("No normalised PYQs provided to structural_dna. Returning minimal scaffold.")
        return _empty_structural_dna()

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    user_message = _build_user_message(normalised_pyqs)

    for attempt in range(1, MAX_RETRIES + 2):
        logger.info("Structural DNA extraction — attempt %d/%d", attempt, MAX_RETRIES + 1)
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_message},
                ],
                temperature=0.0,
                max_tokens=1500,
            )
            raw = response.choices[0].message.content.strip()
            result = _parse_and_validate(raw, normalised_pyqs)
            logger.info("Structural DNA extraction succeeded.")
            return result

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Structural DNA parse error on attempt %d: %s", attempt, e)
            if attempt > MAX_RETRIES:
                raise ValueError(
                    f"Structural DNA failed to produce valid JSON after {MAX_RETRIES + 1} attempts: {e}"
                ) from e
            time.sleep(RETRY_DELAY_SECONDS)

        except Exception as e:
            logger.error("Groq API error on attempt %d: %s", attempt, e)
            if attempt > MAX_RETRIES:
                raise RuntimeError(
                    f"Groq API call failed after {MAX_RETRIES + 1} attempts: {e}"
                ) from e
            time.sleep(RETRY_DELAY_SECONDS)

    return _empty_structural_dna()  # unreachable but satisfies type checker


def _build_user_message(normalised_pyqs: list[dict[str, Any]]) -> str:
    """Assemble the user message from normalised PYQ data."""
    years_summary = []
    for pyq in normalised_pyqs:
        year = pyq.get("year", "unknown")
        question_count = len(pyq.get("questions", []))
        years_summary.append(f"Year {year}: {question_count} questions")

    return (
        f"Extract structural DNA from these {len(normalised_pyqs)} normalised PYQ year(s):\n"
        f"{chr(10).join(years_summary)}\n\n"
        f"Full PYQ data:\n{json.dumps(normalised_pyqs, indent=2)}"
    )


def _parse_and_validate(raw: str, normalised_pyqs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Parse Groq response JSON and fill any missing fields with safe defaults.
    Runs a mechanical fallback for question_distribution if Groq missed it.
    """
    # Strip markdown fences if Groq wrapped the JSON
    clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE).strip()

    result: dict[str, Any] = json.loads(clean)

    # Guarantee required top-level keys exist
    result.setdefault("total_marks", None)
    result.setdefault("time_allowed_minutes", None)
    result.setdefault("sections", [])
    result.setdefault("attempt_all", False)
    result.setdefault("attempt", None)

    # Mechanical fallback: compute question_distribution from raw PYQ data
    # regardless of what Groq returned — this is purely arithmetic and shouldn't
    # require an LLM.
    result["question_distribution"] = _compute_question_distribution(normalised_pyqs)

    # Validate sections have required fields
    for section in result.get("sections", []):
        section.setdefault("section_label", "Main")
        section.setdefault("marks_per_question", None)
        section.setdefault("total_questions", None)
        section.setdefault("attempt_count", None)
        section.setdefault("compulsory", False)

    return result


def _compute_question_distribution(normalised_pyqs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Mechanically compute question distribution per unit across all PYQ years.
    Uses topic_hint → unit mapping from the normalised PYQ data.
    Falls back to question-level unit tags where available.
    """
    from collections import defaultdict

    # unit_number → {appearances: int, marks_per_year: list[int]}
    unit_data: dict[int, dict] = defaultdict(lambda: {"appearances": 0, "marks_list": []})
    num_years = len(normalised_pyqs)

    for pyq in normalised_pyqs:
        year_marks_by_unit: dict[int, int] = defaultdict(int)
        for question in pyq.get("questions", []):
            for part in question.get("parts", []):
                # Unit may be tagged directly on the part, or we fall back to question level
                unit_num = (
                    part.get("unit")
                    or question.get("unit")
                    or 0  # 0 = unknown unit
                )
                marks = part.get("marks", 0)
                unit_data[unit_num]["appearances"] += 1
                year_marks_by_unit[unit_num] += marks

        for unit_num, marks in year_marks_by_unit.items():
            unit_data[unit_num]["marks_list"].append(marks)

    distribution = []
    for unit_num, data in sorted(unit_data.items()):
        marks_list = data["marks_list"]
        avg_marks = round(sum(marks_list) / len(marks_list), 1) if marks_list else 0.0
        distribution.append({
            "unit_number":              unit_num,
            "appearances_across_years": data["appearances"],
            "avg_marks_per_year":       avg_marks,
        })

    return distribution


def _empty_structural_dna() -> dict[str, Any]:
    """Return a safe empty scaffold when no PYQ data is available."""
    return {
        "total_marks":           None,
        "time_allowed_minutes":  None,
        "sections":              [],
        "question_distribution": [],
        "attempt_all":           False,
        "attempt":               None,
    }

def run(raw_pyqs: list[dict]) -> dict:
    return extract_structural_dna(raw_pyqs)
