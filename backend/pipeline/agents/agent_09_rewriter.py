"""
Agent 9 — Rewriter
──────────────────
Receives the Critic's JSON diff (critic_diff_schema.json) and the current topic JSON.
Applies each correction surgically at field level.

Rules:
  - ONLY touches fields listed in the diff.
  - Never rewrites, expands, or improves unflagged fields.
  - Processes critical corrections first, then major, then minor.
  - Each patched field is handed to Agent 9B (micro-validator) before being accepted.
  - On micro-validation failure: retains pre-rewrite value, flags for manual review.
  - Max 2 micro-validation cycles per field.

Model: Gemini 2.0 Flash (free via Google AI Studio)
"""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
_MODEL = "gemini-2.0-flash"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _severity_rank(s: str) -> int:
    return {"critical": 0, "major": 1, "minor": 2}.get(s, 99)


def _build_rewrite_prompt(field: str, current_value: Any, issue: str, correction: str) -> str:
    schema_hint = ""
    if "answer_writing_technique" in field:
        schema_hint = """
━━ EXPECTED SCHEMA FORMAT ━━━━━━━━━━━━━━━━━━━━━━━━━
You MUST output a valid JSON object matching the 'answer_writing_technique' structure:
{
  "applicable": true,
  "min_marks_threshold": 6,
  "structure": ["sentence-by-sentence requirement 1", "sentence-by-sentence requirement 2", ...],
  "marks_distribution": {
    "step or part name": marks_allocated_int,
    ...
  },
  "word_count_target": word_count_int_or_null,
  "diagram_expected": boolean_or_null
}
"""
    elif "diagram_block" in field:
        schema_hint = """
━━ EXPECTED SCHEMA FORMAT ━━━━━━━━━━━━━━━━━━━━━━━━━
You MUST output a valid JSON object matching the 'diagram_block' structure:
{
  "diagram_name": "Name of diagram",
  "svg_source": "library" or "generated",
  "svg_file_path": "library path string or null",
  "svg_code": "svg string or null",
  "labeled_parts": [
    {
      "part_number": 1,
      "part_name": "part name",
      "explanation": "one line explanation",
      "du_expected_label": "exact label"
    }
  ],
  "marks_value": marks_int_or_null,
  "draw_instructions": "step-by-step draw instructions"
}
"""

    return f"""You are the Rewriter agent for StudyAI.
You receive ONE field from a topic JSON that the Critic has flagged.
Your ONLY job: fix the specific issue described. Touch nothing else.

━━ FIELD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Field path : {field}

Current value:
{json.dumps(current_value, ensure_ascii=False, indent=2)}
{schema_hint}
━━ CRITIC FINDING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Issue      : {issue}
Correction : {correction}

━━ RULES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Output ONLY the corrected value for this field — nothing else.
2. Match the exact JSON type of the current value (string → string, array → array, object → object).
3. If the field is a string: output a plain JSON string (no wrapping object).
4. If the field is an array or object: output valid JSON for that structure.
5. All mathematical expressions must be in LaTeX syntax.
6. Do NOT output prose, explanation, or markdown fences.
7. Do NOT invent content not implied by the correction instruction.

Output the corrected field value now:"""


def _resolve_field_path(topic: dict, path: str) -> Any:
    """
    Resolve a dot/bracket path like 'examples[0].steps[2].units_shown'
    to the value at that path in the topic dict.
    Returns (parent_container, final_key, current_value).
    Raises KeyError / IndexError if path doesn't exist.
    """
    import re
    parts = re.split(r'\.|\[(\d+)\]', path)
    # re.split with a group returns empty strings between matches — clean up
    cleaned: list[str | int] = []
    i = 0
    raw_parts = re.findall(r'[^\.\[\]]+|\[\d+\]', path)
    for p in raw_parts:
        if p.startswith('[') and p.endswith(']'):
            cleaned.append(int(p[1:-1]))
        else:
            cleaned.append(p)

    container = topic
    for step in cleaned[:-1]:
        if isinstance(step, int):
            container = container[step]
        else:
            container = container[step]
    return container, cleaned[-1]


def _set_field_path(topic: dict, path: str, value: Any) -> None:
    """Write a value back at a dot/bracket path."""
    container, key = _resolve_field_path(topic, path)
    container[key] = value


def _get_field_path(topic: dict, path: str) -> Any:
    container, key = _resolve_field_path(topic, path)
    if isinstance(key, int):
        return container[key]
    return container[key]


# ─────────────────────────────────────────────────────────────────────────────
# Core rewrite call
# ─────────────────────────────────────────────────────────────────────────────

def _call_rewriter(field: str, current_value: Any, issue: str, correction: str) -> Any:
    """One Gemini Flash call for a single field correction. Returns parsed value."""
    prompt = _build_rewrite_prompt(field, current_value, issue, correction)
    model = genai.GenerativeModel(_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=2048,
        ),
    )
    raw = response.text.strip()

    # Strip markdown fences if model wraps output
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

    # Try JSON parse first; fall back to returning raw string if field is string type or not a known complex structure
    COMPLEX_FIELDS = {"answer_writing_technique", "diagram_block", "pyqs", "examples", "common_mistakes", "quick_checks", "rapid_revision"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        is_complex = any(part in field for part in COMPLEX_FIELDS)
        if isinstance(current_value, str) or (current_value is None and not is_complex):
            return raw  # Plain text correction — valid
        raise ValueError(f"Rewriter returned non-JSON for non-string/complex field '{field}': {raw[:200]}")


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_rewriter(
    topic: dict,
    critic_diff: dict,
    micro_validate_fn: "callable[[str, Any, Any, str, str] -> bool]",
) -> tuple[dict, list[dict]]:
    """
    Apply Critic corrections to the topic dict.

    Args:
        topic            : The full topic JSON dict (will be deep-copied; not mutated in place).
        critic_diff      : Parsed critic_diff_schema.json output from Agent 8.
        micro_validate_fn: Callable from Agent 9B. Signature:
                           (field, original_value, rewritten_value, issue, correction) -> bool

    Returns:
        (patched_topic, rewrite_log)
        rewrite_log: list of dicts recording outcome per correction.
    """
    patched = deepcopy(topic)
    corrections: list[dict] = critic_diff.get("corrections", [])

    # Process in severity order
    ordered = sorted(corrections, key=lambda c: _severity_rank(c.get("severity", "minor")))

    rewrite_log: list[dict] = []

    for correction in ordered:
        field     = correction["field"]
        issue     = correction["issue"]
        fix       = correction["correction"]
        severity  = correction["severity"]

        log_entry: dict = {
            "field":    field,
            "severity": severity,
            "issue":    issue,
            "status":   None,
        }

        # ── Retrieve current value ──────────────────────────────────────────
        try:
            original_value = _get_field_path(patched, field)
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Rewriter: cannot resolve field path '%s' — %s", field, exc)
            log_entry["status"] = "path_error"
            log_entry["error"]  = str(exc)
            rewrite_log.append(log_entry)
            continue

        # ── Attempt rewrite with micro-validation (max 2 cycles) ───────────
        accepted = False
        last_rewritten = None

        for attempt in range(1, 3):
            try:
                rewritten_value = _call_rewriter(field, original_value, issue, fix)
            except Exception as exc:
                logger.error(
                    "Rewriter: Gemini call failed on attempt %d for field '%s' — %s",
                    attempt, field, exc
                )
                log_entry["status"] = "api_error"
                log_entry["error"]  = str(exc)
                break

            last_rewritten = rewritten_value

            # Micro-validation
            valid = micro_validate_fn(field, original_value, rewritten_value, issue, fix)

            if valid:
                _set_field_path(patched, field, rewritten_value)
                accepted = True
                log_entry["status"]    = "accepted"
                log_entry["attempt"]   = attempt
                log_entry["new_value"] = rewritten_value
                logger.info("Rewriter: ✓ field '%s' accepted on attempt %d", field, attempt)
                break
            else:
                logger.warning(
                    "Rewriter: micro-validation failed for '%s' on attempt %d", field, attempt
                )

        if not accepted:
            # Retain pre-rewrite value — flag for manual review
            log_entry["status"]          = "manual_review"
            log_entry["rejected_value"]  = last_rewritten
            log_entry["retained_value"]  = original_value
            logger.error(
                "Rewriter: field '%s' failed both micro-validation cycles → manual review", field
            )

        rewrite_log.append(log_entry)

    return patched, rewrite_log


# ─────────────────────────────────────────────────────────────────────────────
# Standalone execution helper (for testing)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python 09_rewriter.py <topic_json_path> <critic_diff_json_path>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        _topic = json.load(f)

    with open(sys.argv[2]) as f:
        _diff = json.load(f)

    # Stub micro-validator that always accepts (replace with real 09b import in production)
    def _stub_validator(field, orig, new, issue, correction):
        print(f"  [stub-validator] accepting field: {field}")
        return True

    _patched, _log = run_rewriter(_topic, _diff, _stub_validator)

    print("\n── Rewrite log ──")
    for entry in _log:
        status = entry["status"]
        icon = "✓" if status == "accepted" else ("⚠" if status == "manual_review" else "✗")
        print(f"  {icon}  {entry['field']} ({entry['severity']}) → {status}")

    out_path = sys.argv[1].replace(".json", "_rewritten.json")
    with open(out_path, "w") as f:
        json.dump(_patched, f, ensure_ascii=False, indent=2)
    print(f"\nPatched topic written to: {out_path}")

async def run(topic: dict, diff: dict, paper: dict, cost=None) -> dict:
    import asyncio
    from pipeline.agents.agent_09b_micro_validator import validate_rewritten_field
    patched_topic, rewrite_log = await asyncio.to_thread(
        run_rewriter, topic, diff, validate_rewritten_field
    )
    return patched_topic
