"""
Agent 11B — Post-Patch Regenerator
────────────────────────────────────
For every topic modified by the Patcher (Agent 11), regenerates exactly three fields:

  1. rapid_revision        — must reflect ALL content including newly patched fields
  2. quick_checks          — exactly 3, no answers, at least 1 requires application
  3. connects_to_reason    — one sentence reflecting current topic state

These three fields are the "living summary" of a topic — they must always reflect
the final, complete state. If a topic was patched, these fields are stale.

Rules:
  - Only regenerates these three fields. Nothing else.
  - If regeneration fails: retains pre-patch values, logs as flagged.
  - One Gemini call per patched topic (batches all 3 fields in one call).

Model: Gemini 2.0 Flash
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
# Prompt
# ─────────────────────────────────────────────────────────────────────────────

_REGEN_SYSTEM = """You are the Post-Patch Regenerator for StudyAI.
A topic has been patched. You regenerate exactly three fields to reflect the final state.

Rules:
- Output ONLY valid JSON with exactly three keys: rapid_revision, quick_checks, connects_to_reason.
- rapid_revision: { definition_one_line (≤15 words), key_formula_or_concept, examiner_pattern }
  definition_one_line must contain minimum viable exam knowledge.
  examiner_pattern must contain the exact DU instruction word for this topic.
- quick_checks: exactly 3 strings, no answers ever, at least 1 requires application not recall.
- connects_to_reason: one sentence — how this topic connects to the next topic in the unit.
- All math in LaTeX.
- No prose. No markdown fences. Output only valid JSON."""


def _build_regen_prompt(topic: dict) -> str:
    return f"""TOPIC (final patched state):
{json.dumps(topic, ensure_ascii=False, indent=2)}

Generate the three summary fields now. Output only valid JSON."""


# ─────────────────────────────────────────────────────────────────────────────
# Gemini call
# ─────────────────────────────────────────────────────────────────────────────

def _call_regen(topic: dict, attempt: int = 1) -> dict | None:
    prompt = _build_regen_prompt(topic)
    model  = genai.GenerativeModel(_MODEL, system_instruction=_REGEN_SYSTEM)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=1024,
                response_mime_type="application/json",
            ),
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        parsed = json.loads(raw)

        # Validate presence of all three keys
        required = {"rapid_revision", "quick_checks", "connects_to_reason"}
        if not required.issubset(parsed.keys()):
            raise ValueError(f"Missing keys: {required - parsed.keys()}")

        # Validate quick_checks count
        if not isinstance(parsed["quick_checks"], list) or len(parsed["quick_checks"]) != 3:
            raise ValueError(
                f"quick_checks must be a list of exactly 3 items "
                f"(got {len(parsed.get('quick_checks', []))})"
            )

        # Validate rapid_revision structure
        rr = parsed["rapid_revision"]
        for key in ("definition_one_line", "key_formula_or_concept", "examiner_pattern"):
            if key not in rr:
                raise ValueError(f"rapid_revision missing key: {key}")

        word_count = len(rr["definition_one_line"].split())
        if word_count > 15:
            raise ValueError(
                f"rapid_revision.definition_one_line exceeds 15 words ({word_count})"
            )

        return parsed

    except Exception as exc:
        if attempt < 2:
            logger.warning(
                "11B: regen attempt %d failed for topic '%s' — %s — retrying",
                attempt, topic.get("topic_name"), exc
            )
            return _call_regen(topic, attempt + 1)

        logger.error(
            "11B: regen failed after 2 attempts for topic '%s' — retaining pre-patch values. Error: %s",
            topic.get("topic_name"), exc
        )
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_post_patch_regen(patched_topics: list[dict]) -> list[dict]:
    """
    Args:
        patched_topics : List of topic dicts in their final post-patch state.
                         Each must have at minimum: topic_name, definition, core_concept,
                         examples, pyqs, rapid_revision (pre-patch), quick_checks (pre-patch).

    Returns:
        List of dicts:
        [
            {
                "topic_id": str,
                "rapid_revision": {...},
                "quick_checks": [...],
                "connects_to_reason": str,
                "regen_status": "success" | "fallback",
            },
            ...
        ]
    """
    results: list[dict] = []

    for topic in patched_topics:
        topic_id   = topic.get("id", "unknown")
        topic_name = topic.get("topic_name", "unknown")

        logger.info("11B: regenerating summary fields for topic '%s'", topic_name)
        regen = _call_regen(topic)

        if regen is not None:
            results.append({
                "topic_id":          topic_id,
                "rapid_revision":    regen["rapid_revision"],
                "quick_checks":      regen["quick_checks"],
                "connects_to_reason": regen["connects_to_reason"],
                "regen_status":      "success",
            })
            logger.info("11B: ✓ '%s' regenerated successfully", topic_name)
        else:
            # Fallback — retain pre-patch values
            results.append({
                "topic_id":          topic_id,
                "rapid_revision":    topic.get("rapid_revision"),
                "quick_checks":      topic.get("quick_checks"),
                "connects_to_reason": topic.get("connects_to_reason"),
                "regen_status":      "fallback",
            })
            logger.warning("11B: ⚠ '%s' using pre-patch values (fallback)", topic_name)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python 11b_post_patch_regen.py <patched_topics_json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        _topics = json.load(f)

    _results = run_post_patch_regen(_topics)

    print(f"\nRegenerated {len(_results)} topics:")
    for r in _results:
        icon = "✓" if r["regen_status"] == "success" else "⚠"
        print(f"  {icon}  {r['topic_id'][:8]}…  ({r['regen_status']})")
        if r["rapid_revision"]:
            print(f"      RR: {r['rapid_revision'].get('definition_one_line', '')[:60]}")

async def run(patched_topic_ids: list[str], unit: dict, paper: dict, cost=None) -> dict:
    from database import queries as q
    import asyncio
    patched_topics = [q.get_topic(tid) for tid in patched_topic_ids]
    patched_topics = [t for t in patched_topics if t]
    result = await asyncio.to_thread(run_post_patch_regen, patched_topics)
    return {"topic_regens": result}

async def run_unit_summary(unit: dict, topics: list[dict], paper: dict, cost=None) -> dict:
    return {"conceptual_summary": {}, "unit_closer": {}}
