"""
Agent 11 — Patcher
──────────────────
Receives Final Examiner output and patches what is missing.
Works at field level only — never modifies unflagged fields.

Four tasks:
  TASK 1 — Add uncovered PYQs to the correct topic's pyqs array.
  TASK 2 — Complete marks-incomplete topics (add missing fields only).
  TASK 3 — Post-patch regeneration (rapid_revision, quick_checks,
            connects_to_reason) for every patched topic.
  TASK 4 — Regenerate unit conceptual_summary if any topic in the unit was patched.

After every patch, Agent 11B (post-patch regenerator) handles Task 3.

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

_PATCHER_PROMPT = open(
    os.path.join(os.path.dirname(__file__), "..", "prompts", "patcher.txt"),
    encoding="utf-8",
).read()

_UNIT_SCHEMA = json.load(
    open(os.path.join(os.path.dirname(__file__), "..", "schemas", "unit_schema.json"))
)

# ─────────────────────────────────────────────────────────────────────────────
# Task 1 — Add missing PYQs
# ─────────────────────────────────────────────────────────────────────────────

def _build_pyq_patch_prompt(uncovered_pyq: dict, topic: dict) -> str:
    return f"""You are the Patcher agent for StudyAI.

One PYQ is not covered in the current topic notes. Add it.

UNCOVERED PYQ:
{json.dumps(uncovered_pyq, ensure_ascii=False, indent=2)}

TOPIC (current state):
Name: {topic.get('topic_name')}
Existing PYQs: {json.dumps(topic.get('pyqs', []), ensure_ascii=False, indent=2)}

Generate ONLY the new PYQ object to append to the pyqs array.
It must conform to this structure exactly:
{{
  "year": integer,
  "year_confirmed": boolean,
  "year_confidence": "confirmed" | "unconfirmed",
  "source": "string",
  "marks": integer,
  "question_text": "string — exact question text, not paraphrased",
  "key_steps": ["string", ...],
  "instruction_word": "string",
  "recency_weight": number
}}

key_steps must be specific enough to earn full marks at DU — not generic.
Output only valid JSON. No other text."""


def _build_field_patch_prompt(topic: dict, missing_fields: list[str]) -> str:
    fields_str = "\n".join(f"  - {f}" for f in missing_fields)
    return f"""You are the Patcher agent for StudyAI.
A topic is missing required fields for its marks level. Generate ONLY the missing fields.

TOPIC (current state):
{json.dumps(topic, ensure_ascii=False, indent=2)}

MISSING FIELDS TO GENERATE:
{fields_str}

Rules:
- Generate ONLY the listed missing fields.
- Do NOT regenerate or touch any other field.
- All mathematical expressions in LaTeX.
- answer_writing_technique (if requested): must include structure (list of strings),
  marks_distribution (object), word_count_target (integer), applicable: true,
  min_marks_threshold (integer).
- examples (if requested): numerical examples must have units on every intermediate step,
  answer_boxed: true, verified: false.
- Output a single JSON object with ONLY the requested fields as keys.
- No prose. No markdown. No other text.

Output:"""


def _gemini_call(prompt: str) -> Any:
    model = genai.GenerativeModel(_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=4096,
        ),
    )
    raw = response.text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Task 4 — Unit conceptual summary
# ─────────────────────────────────────────────────────────────────────────────

def _build_unit_summary_prompt(unit_topics: list[dict], unit_name: str) -> str:
    topic_names_and_concepts = [
        {
            "topic_name":  t.get("topic_name"),
            "definition":  t.get("definition", ""),
            "core_concept": t.get("core_concept", ""),
        }
        for t in unit_topics
    ]
    return f"""You are the Patcher agent for StudyAI.
One or more topics in this unit were patched. Regenerate the unit conceptual summary.

UNIT NAME: {unit_name}

ALL TOPICS IN UNIT (final state):
{json.dumps(topic_names_and_concepts, ensure_ascii=False, indent=2)}

Generate ONLY this JSON object:
{{
  "what_this_unit_is_about": "2 plain sentences — what the unit covers as a whole",
  "how_topics_connect": "1-2 sentences — how the topics build on each other",
  "unifying_idea": "1 sentence — the single anchor concept that ties all topics together"
}}

No prose. No markdown. Output only valid JSON."""


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_patcher(
    unit_topics: list[dict],
    examiner_output: dict,
    unit_name: str,
    topic_lookup_fn: "callable[[str], str]",  # topic_hint -> topic_id
) -> dict:
    """
    Args:
        unit_topics       : All topic dicts for this unit (full content from DB).
        examiner_output   : Output from run_final_examiner().
        unit_name         : Name of the unit being patched.
        topic_lookup_fn   : Given a topic_hint string, returns the matching topic_id.

    Returns:
        Patcher output dict conforming to patcher output schema:
        {
            "topic_patches": [{ "topic_id": str, "patched_fields": {...} }],
            "unit_patches":  [{ "unit_id": str, "conceptual_summary": {...} }],
        }
    """
    topics_by_id = {t["id"]: deepcopy(t) for t in unit_topics}
    patched_topic_ids: set[str] = set()
    topic_patches: dict[str, dict] = {}  # topic_id -> accumulated patched_fields

    # ── TASK 1: Add uncovered PYQs ──────────────────────────────────────────
    for uq in examiner_output.get("uncovered_pyqs", []):
        topic_id = topic_lookup_fn(uq.get("topic_hint", ""))
        if not topic_id or topic_id not in topics_by_id:
            logger.warning("Patcher: cannot locate topic for PYQ hint '%s'", uq.get("topic_hint"))
            continue

        topic = topics_by_id[topic_id]

        try:
            new_pyq = _gemini_call(_build_pyq_patch_prompt(uq, topic))
        except Exception as exc:
            logger.error("Patcher: PYQ patch call failed for topic '%s' — %s", topic_id, exc)
            continue

        # Append to topic's pyqs in our working copy
        if "pyqs" not in topic:
            topic["pyqs"] = []
        topic["pyqs"].append(new_pyq)

        # Record in patch output
        if topic_id not in topic_patches:
            topic_patches[topic_id] = {}
        topic_patches[topic_id]["pyqs"] = topic["pyqs"]
        patched_topic_ids.add(topic_id)

        logger.info(
            "Patcher: added uncovered PYQ (%d marks, %s) to topic '%s'",
            uq.get("marks", 0), uq.get("year"), topic.get("topic_name")
        )

    # ── TASK 2: Complete marks-incomplete topics ─────────────────────────────
    for incomplete in examiner_output.get("marks_incomplete_topics", []):
        topic_name     = incomplete.get("topic_name", "")
        missing_fields = incomplete.get("missing_fields", [])

        if not missing_fields:
            continue

        # Find topic by name
        topic_id = next(
            (tid for tid, t in topics_by_id.items()
             if t.get("topic_name", "").strip().lower() == topic_name.strip().lower()),
            None,
        )
        if not topic_id:
            logger.warning("Patcher: topic '%s' not found — skipping", topic_name)
            continue

        topic = topics_by_id[topic_id]

        try:
            new_fields = _gemini_call(_build_field_patch_prompt(topic, missing_fields))
        except Exception as exc:
            logger.error(
                "Patcher: field patch call failed for topic '%s' — %s", topic_name, exc
            )
            continue

        # Apply only the requested missing fields
        if topic_id not in topic_patches:
            topic_patches[topic_id] = {}
        for fld in missing_fields:
            if fld in new_fields:
                topic[fld] = new_fields[fld]
                topic_patches[topic_id][fld] = new_fields[fld]
        patched_topic_ids.add(topic_id)

        logger.info(
            "Patcher: patched missing fields %s on topic '%s'", missing_fields, topic_name
        )

    # ── TASK 3: Post-patch regeneration (rapid_revision, quick_checks,
    #            connects_to_reason) — delegated to Agent 11B ───────────────
    # We build the list of patched topic states here; 11B will do the calls.
    patched_topics_state = [
        topics_by_id[tid] for tid in patched_topic_ids if tid in topics_by_id
    ]

    # ── TASK 4: Unit conceptual summary ─────────────────────────────────────
    unit_patches: list[dict] = []

    if patched_topic_ids:
        try:
            all_final_topics = list(topics_by_id.values())
            new_summary = _gemini_call(
                _build_unit_summary_prompt(all_final_topics, unit_name)
            )
            # unit_id is set by the orchestrator — we return a placeholder
            unit_patches.append({
                "unit_name": unit_name,
                "conceptual_summary": new_summary,
            })
            logger.info("Patcher: regenerated conceptual_summary for unit '%s'", unit_name)
        except Exception as exc:
            logger.error("Patcher: unit summary regeneration failed — %s", exc)

    return {
        "topic_patches":        [
            {"topic_id": tid, "patched_fields": patches}
            for tid, patches in topic_patches.items()
        ],
        "patched_topics_state": patched_topics_state,
        "unit_patches":         unit_patches,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python 11_patcher.py <topics_json> <examiner_output_json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        _topics = json.load(f)
    with open(sys.argv[2]) as f:
        _examiner = json.load(f)

    # Stub lookup
    def _stub_lookup(hint: str) -> str | None:
        hint_lower = hint.lower()
        for t in _topics:
            if hint_lower in t.get("topic_name", "").lower():
                return t["id"]
        return None

    _result = run_patcher(_topics, _examiner, "Unit 1 — Sequences", _stub_lookup)

    print(f"\nTopic patches  : {len(_result['topic_patches'])}")
    print(f"Unit patches   : {len(_result['unit_patches'])}")

    out_path = "patcher_output.json"
    with open(out_path, "w") as f:
        json.dump(_result, f, ensure_ascii=False, indent=2)
    print(f"Output written to: {out_path}")

async def run(unit: dict, topics: list[dict], examiner_output: dict, paper: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_patcher, unit, topics, examiner_output)
