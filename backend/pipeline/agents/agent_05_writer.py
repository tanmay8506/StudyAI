"""
05_writer.py
-------------
Agent 5 — Writer
Model:      Claude Sonnet 4.6  (claude-sonnet-4-6)
Role:       Core content generation. Runs per topic.

This is the most important agent in the pipeline. It takes a single topic,
all its DNA signals, and the prerequisite bridge from Agent 4, and produces
the complete topic JSON that will be rendered to students.

Architecture decisions:
  - System prompt (writer_invariant.txt) is cached via the Anthropic API's
    prompt caching feature. This is set up via cache_control on the system block.
    Saves 60–70% of Writer token cost across an entire paper run.
  - User message is built dynamically per topic by writer_variant.py.
  - Retries: max 3 attempts with incrementally explicit schema constraints.
  - Split generation: if a topic is flagged split_generation=True by Agent 4,
    this agent runs two calls (content + examples) and merges the results.
  - Schema validation: jsonschema validates output before any database write.
  - LaTeX auto-fix: latex_formatter.py catches common LaTeX errors before
    sending to Critic. Residual errors become Critic flags.

Called by:  backend/pipeline/orchestrator.py
  - Once per topic, in the optimised sequence provided by Agent 4.
  - Orchestrator updates topics.status: queued → generating → complete / failed.

Inputs (from orchestrator):
  - topic_row: dict   — current row from Supabase topics table
  - unit_row: dict    — parent unit row
  - paper_row: dict   — parent paper row (includes paper_dna)
  - mapper_output: dict  — Agent 4's full output (for concept bridges)

Outputs:
  - Writes the validated topic JSON to the Supabase topics table (field by field).
  - Returns the validated dict for downstream agents (Coverage Checker, etc.)
  - On failure: writes status='failed', failure_reason to flagged_fields.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import groq
import jsonschema
from dotenv import load_dotenv

# ── Internal imports ─────────────────────────────────────────────────────────
# Adjust relative paths if your working directory differs.
from pipeline.prompts.writer_variant import build_writer_user_prompt
from utils.latex_formatter import auto_fix_latex          # Phase 7 utility
from database.queries import set_topic_status              # Phase 7 db layer
from database.client import db

# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()
logger = logging.getLogger(__name__)

import google.generativeai as genai

# ── Model ─────────────────────────────────────────────────────────────────────
WRITER_MODEL = "gemini-2.0-flash"

# ── Retry policy ──────────────────────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5    # Exponential backoff: attempt N waits N * RETRY_DELAY_SECONDS

# ── File paths ────────────────────────────────────────────────────────────────
PROMPTS_DIR   = Path(__file__).parent.parent / "prompts"
SCHEMAS_DIR   = Path(__file__).parent.parent / "schemas"

INVARIANT_PROMPT_PATH = PROMPTS_DIR / "writer_invariant.txt"
TOPIC_SCHEMA_PATH     = SCHEMAS_DIR / "topic_schema.json"

# ── Load once at module import ────────────────────────────────────────────────
# These are loaded once per process, not per topic call.

def _load_invariant_prompt() -> str:
    """Load the cached system prompt. Exits hard on missing file — this is a
    build error, not a runtime error."""
    path = INVARIANT_PROMPT_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Writer invariant prompt not found at {path}. "
            "Have you completed Phase 4 setup? "
            "Expected: backend/pipeline/prompts/writer_invariant.txt"
        )
    return path.read_text(encoding="utf-8")

def _load_topic_schema() -> dict:
    path = TOPIC_SCHEMA_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"topic_schema.json not found at {path}. "
            "Expected: backend/pipeline/schemas/topic_schema.json"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)

INVARIANT_SYSTEM_PROMPT: str  = _load_invariant_prompt()
TOPIC_SCHEMA: dict            = _load_topic_schema()

# ── Anthropic client (now Groq) ───────────────────────────────────────────────
# client instantiated per call


# ─────────────────────────────────────────────────────────────────────────────
#  Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_writer(
    topic_row: dict,
    unit_row: dict,
    paper_row: dict,
    mapper_output: dict,
) -> dict | None:
    """
    Run Agent 5 for a single topic.

    Returns the validated topic dict on success, or None on terminal failure.
    Writes status updates to Supabase throughout.

    Handles split_generation automatically — the caller does not need to manage
    the split/merge logic.
    """
    topic_id   = topic_row["id"]
    topic_name = topic_row["topic_name"]
    upc        = topic_row["upc"]

    logger.info(f"[Writer] Starting topic: '{topic_name}' (id={topic_id}, upc={upc})")
    set_topic_status(topic_id, "generating")

    # ── Extract DNA signals for this specific topic ───────────────────────────
    paper_dna     = paper_row.get("paper_dna") or {}
    topic_dna     = _extract_topic_dna(paper_dna, topic_name)
    language_dna  = _extract_language_dna(paper_dna, topic_name)
    combination_dna = _extract_combination_dna(paper_dna, topic_name)

    # ── Extract Agent 4 mapping signals ──────────────────────────────────────
    concept_bridge, left_adj, right_adj = _extract_mapper_signals(
        mapper_output, topic_row["id"], topic_row.get("topic_number", 0)
    )

    # ── Build the user message ────────────────────────────────────────────────
    split_generation = topic_row.get("split_generation", False)

    if split_generation:
        result = _run_split_generation(
            topic_row=topic_row,
            paper_row=paper_row,
            topic_dna=topic_dna,
            language_dna=language_dna,
            combination_dna=combination_dna,
            concept_bridge=concept_bridge,
            left_adj=left_adj,
            right_adj=right_adj,
        )
    else:
        result = _run_single_generation(
            topic_row=topic_row,
            paper_row=paper_row,
            topic_dna=topic_dna,
            language_dna=language_dna,
            combination_dna=combination_dna,
            concept_bridge=concept_bridge,
            left_adj=left_adj,
            right_adj=right_adj,
        )

    if result is None:
        logger.error(f"[Writer] Terminal failure for topic '{topic_name}' after all retries.")
        set_topic_status(topic_id, "failed")
        db.table("topics").update({
            "flagged_fields": {
                "generation_failure": "Writer failed schema validation after max retries."
            }
        }).eq("id", topic_id).execute()
        return None

    # ── Apply LaTeX auto-fix before writing to DB ─────────────────────────────
    result = auto_fix_latex(result)

    # ── Write to Supabase ─────────────────────────────────────────────────────
    _write_topic_to_db(topic_id, result)
    set_topic_status(topic_id, "verifying")    # Orchestrator picks up from here for Agent 6

    logger.info(f"[Writer] ✓ Topic complete: '{topic_name}' (priority={result.get('priority')})")
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  Internal: single-call generation
# ─────────────────────────────────────────────────────────────────────────────

def _run_single_generation(
    topic_row: dict,
    paper_row: dict,
    topic_dna: dict | None,
    language_dna: dict | None,
    combination_dna: dict | None,
    concept_bridge: str | None,
    left_adj: str | None,
    right_adj: str | None,
) -> dict | None:
    """
    Standard generation path. One API call produces the complete topic JSON.
    Returns the validated dict or None on terminal failure.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        user_message = build_writer_user_prompt(
            topic_name=topic_row["topic_name"],
            topic_syllabus_content=_get_syllabus_content(topic_row),
            topic_dna=topic_dna,
            language_dna=language_dna,
            combination_dna=combination_dna,
            concept_bridge=concept_bridge,
            left_adjacent_topic=left_adj,
            right_adjacent_topic=right_adj,
            note_style_category=paper_row.get("paper_type", "theory"),
            diagram_heavy=paper_row.get("diagram_heavy", False),
            primary_textbook=paper_row.get("primary_textbook"),
            documentation_tier=paper_row.get("documentation_tier", 2),
            upc=topic_row["upc"],
            split_generation=False,
            split_mode=None,
        )

        # On retries: append constraint escalation to user message
        if attempt > 1:
            user_message = _escalate_retry_constraints(user_message, attempt)

        result = _call_writer_api(user_message, attempt)
        if result is None:
            logger.warning(f"[Writer] Attempt {attempt}/{MAX_RETRIES}: API call failed or returned non-JSON.")
            _sleep_before_retry(attempt)
            continue

        validated = _validate_schema(result, attempt)
        if validated is not None:
            return validated

        logger.warning(f"[Writer] Attempt {attempt}/{MAX_RETRIES}: Schema validation failed.")
        _sleep_before_retry(attempt)

    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Internal: split generation (for topics flagged by Agent 4)
# ─────────────────────────────────────────────────────────────────────────────

def _run_split_generation(
    topic_row: dict,
    paper_row: dict,
    topic_dna: dict | None,
    language_dna: dict | None,
    combination_dna: dict | None,
    concept_bridge: str | None,
    left_adj: str | None,
    right_adj: str | None,
) -> dict | None:
    """
    Two-call generation for topics flagged split_generation=True by Agent 4.

    Call 1: Generate all fields EXCEPT examples and pyqs.
    Call 2: Generate ONLY examples and pyqs.
    Merge: combine the two outputs into one validated dict.

    This route is triggered when Agent 4 sets split_generation=True because
    the topic is estimated to exceed 6,000 output tokens in a single call.
    """
    topic_name = topic_row["topic_name"]
    logger.info(f"[Writer] Split generation mode activated for '{topic_name}'.")

    # Common kwargs for both calls
    base_kwargs = dict(
        topic_name=topic_name,
        topic_syllabus_content=_get_syllabus_content(topic_row),
        topic_dna=topic_dna,
        language_dna=language_dna,
        combination_dna=combination_dna,
        concept_bridge=concept_bridge,
        left_adjacent_topic=left_adj,
        right_adjacent_topic=right_adj,
        note_style_category=paper_row.get("paper_type", "theory"),
        diagram_heavy=paper_row.get("diagram_heavy", False),
        primary_textbook=paper_row.get("primary_textbook"),
        documentation_tier=paper_row.get("documentation_tier", 2),
        upc=topic_row["upc"],
        split_generation=True,
    )

    # ── Call 1: Content ───────────────────────────────────────────────────────
    content_result = None
    for attempt in range(1, MAX_RETRIES + 1):
        msg = build_writer_user_prompt(**base_kwargs, split_mode="content")
        if attempt > 1:
            msg = _escalate_retry_constraints(msg, attempt)

        raw = _call_writer_api(msg, attempt)
        if raw is None:
            _sleep_before_retry(attempt)
            continue

        # Content call: allow examples=[] and pyqs=[] — they are intentionally empty
        # Validate with a relaxed check on those two fields
        validated = _validate_schema(raw, attempt, allow_empty_examples=True)
        if validated is not None:
            content_result = validated
            break
        _sleep_before_retry(attempt)

    if content_result is None:
        logger.error(f"[Writer] Split content call failed for '{topic_name}'.")
        return None

    # ── Call 2: Examples ──────────────────────────────────────────────────────
    examples_result = None
    for attempt in range(1, MAX_RETRIES + 1):
        msg = build_writer_user_prompt(**base_kwargs, split_mode="examples")
        if attempt > 1:
            msg = _escalate_retry_constraints(msg, attempt)

        raw = _call_writer_api(msg, attempt)
        if raw is None:
            _sleep_before_retry(attempt)
            continue

        # Examples call only needs examples and pyqs — validate those fields
        validated = _validate_examples_only(raw, attempt)
        if validated is not None:
            examples_result = validated
            break
        _sleep_before_retry(attempt)

    if examples_result is None:
        logger.error(f"[Writer] Split examples call failed for '{topic_name}'.")
        # Don't abandon — return content_result with empty examples.
        # Critic will flag missing examples. Patcher (Agent 11) can fill them.
        logger.warning(f"[Writer] Proceeding with content-only result for '{topic_name}'. Examples will be flagged.")
        content_result["flagged_fields"] = content_result.get("flagged_fields") or {}
        content_result["flagged_fields"]["examples"] = "split_examples_call_failed"
        return content_result

    # ── Merge ─────────────────────────────────────────────────────────────────
    merged = _merge_split_results(content_result, examples_result)
    final  = _validate_schema(merged, attempt=0)

    if final is None:
        logger.error(f"[Writer] Merged split result failed full schema validation for '{topic_name}'.")
        # Return content_result as fallback — partial is better than nothing.
        content_result["flagged_fields"] = content_result.get("flagged_fields") or {}
        content_result["flagged_fields"]["split_merge"] = "merge_schema_validation_failed"
        return content_result

    logger.info(f"[Writer] ✓ Split generation complete for '{topic_name}'.")
    return final


def _merge_split_results(content: dict, examples: dict) -> dict:
    """
    Merge the content call output and the examples call output into one dict.
    The content call output is the base; examples and pyqs are overwritten
    with the examples call output.
    """
    merged = content.copy()
    merged["examples"] = examples.get("examples") or []
    merged["pyqs"]     = examples.get("pyqs") or []
    return merged


# ─────────────────────────────────────────────────────────────────────────────
#  Internal: API call
# ─────────────────────────────────────────────────────────────────────────────

def _call_writer_api(user_message: str, attempt: int) -> dict | None:
    """
    Make one call to the Gemini API.
    Returns the parsed dict or None if parsing fails.
    """
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(
            model_name=WRITER_MODEL,
            generation_config={"response_mime_type": "application/json"}
        )
        
        system_content = INVARIANT_SYSTEM_PROMPT + "\n\nSCHEMA EXACT SPECIFICATION:\n" + json.dumps(TOPIC_SCHEMA, indent=2)
        
        full_prompt = system_content + "\n\n" + user_message
        
        response = model.generate_content(full_prompt)
        raw_text = response.text.strip()

        # Strip any accidental markdown fences
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:])
            if raw_text.rstrip().endswith("```"):
                raw_text = raw_text.rstrip()[:-3].rstrip()

        parsed = json.loads(raw_text)
        return parsed

    except json.JSONDecodeError as e:
        logger.warning(
            f"[Writer] Attempt {attempt}: JSON parse error: {e}. "
            f"First 200 chars of response: {raw_text[:200] if 'raw_text' in dir() else 'N/A'}"
        )
        return None

    except Exception as e:
        logger.error(f"[Writer] Attempt {attempt}: Unexpected error: {type(e).__name__}: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  Internal: schema validation
# ─────────────────────────────────────────────────────────────────────────────

def _validate_schema(
    data: dict,
    attempt: int,
    allow_empty_examples: bool = False,
) -> dict | None:
    """
    Validate the Writer output against topic_schema.json.
    Returns the validated dict on success, or None on failure.

    allow_empty_examples=True is used for the split content call only,
    where examples=[] and pyqs=[] are valid and intentional.
    """
    try:
        jsonschema.validate(instance=data, schema=TOPIC_SCHEMA)
        return data
    except jsonschema.ValidationError as e:
        # If allow_empty_examples and the only error is about examples/pyqs, pass
        if allow_empty_examples and _error_is_only_empty_arrays(e):
            return data
        logger.warning(
            f"[Writer] Attempt {attempt}: Schema validation error: "
            f"{e.message} at path {list(e.absolute_path)}"
        )
        return None
    except jsonschema.SchemaError as e:
        # This is a bug in our schema, not in the Writer output
        logger.error(f"[Writer] Schema file error (bug): {e.message}")
        raise  # Escalate — this needs a developer fix


def _validate_examples_only(data: dict, attempt: int) -> dict | None:
    """
    Lightweight validation for the examples-only split call.
    Only checks that examples and pyqs are valid arrays.
    Does not run full schema validation.
    """
    if not isinstance(data, dict):
        logger.warning(f"[Writer] Examples call attempt {attempt}: Result is not a dict.")
        return None
    if "examples" not in data or not isinstance(data.get("examples"), list):
        logger.warning(f"[Writer] Examples call attempt {attempt}: examples field missing or not a list.")
        return None
    if "pyqs" not in data or not isinstance(data.get("pyqs"), list):
        logger.warning(f"[Writer] Examples call attempt {attempt}: pyqs field missing or not a list.")
        return None
    return data


def _error_is_only_empty_arrays(e: jsonschema.ValidationError) -> bool:
    """Check if a validation error is solely about empty examples/pyqs arrays."""
    path = list(e.absolute_path)
    return len(path) > 0 and path[0] in ("examples", "pyqs")


# ─────────────────────────────────────────────────────────────────────────────
#  Internal: retry escalation
# ─────────────────────────────────────────────────────────────────────────────

_RETRY_ESCALATION = [
    "",  # attempt 1: no escalation
    (
        "\n\n━━ RETRY CONSTRAINT ESCALATION — ATTEMPT 2 ━━\n"
        "Your previous output failed JSON schema validation.\n"
        "Common causes:\n"
        "  1. Missing required fields (rapid_revision, common_mistakes, pyqs, quick_checks)\n"
        "  2. quick_checks does not have exactly 3 items\n"
        "  3. common_mistakes has 0 items (minimum 1 required)\n"
        "  4. priority value not in ['high', 'medium', 'low', 'never_asked']\n"
        "  5. Output included prose or markdown fences around the JSON\n"
        "Correct these and output only valid JSON starting with { and ending with }."
    ),
    (
        "\n\n━━ RETRY CONSTRAINT ESCALATION — ATTEMPT 3 (FINAL) ━━\n"
        "Two previous outputs failed validation. This is your final attempt.\n"
        "MANDATORY SIMPLIFICATION RULES:\n"
        "  - If in doubt about a field value: set it to null (never omit the key)\n"
        "  - quick_checks: exactly 3 strings in an array — no more, no less\n"
        "  - common_mistakes: exactly 1 object with 'description' and 'marks_impact'\n"
        "  - rapid_revision: all three keys present (definition_one_line, key_formula_or_concept, examiner_pattern)\n"
        "  - pyqs: [] is acceptable if no PYQ data is available\n"
        "  - examples: [] is acceptable if no examples can be generated\n"
        "Output ONLY the JSON object. Nothing before {. Nothing after }."
    ),
]

def _escalate_retry_constraints(user_message: str, attempt: int) -> str:
    """Append escalating constraints on retry attempts 2 and 3."""
    if attempt <= 1 or attempt - 1 >= len(_RETRY_ESCALATION):
        return user_message
    return user_message + _RETRY_ESCALATION[attempt - 1]


# ─────────────────────────────────────────────────────────────────────────────
#  Internal: DNA extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_topic_dna(paper_dna: dict, topic_name: str) -> dict | None:
    """Find this topic's entry in the paper_dna topic_dna array."""
    topic_dna_list = paper_dna.get("topic_dna") or []
    for entry in topic_dna_list:
        if entry.get("topic_name", "").strip().lower() == topic_name.strip().lower():
            return entry
    return None


def _extract_language_dna(paper_dna: dict, topic_name: str) -> dict | None:
    """Find this topic's entry in the paper_dna language_dna array."""
    language_dna_list = paper_dna.get("language_dna") or []
    for entry in language_dna_list:
        if entry.get("topic_name", "").strip().lower() == topic_name.strip().lower():
            return entry
    return None


def _extract_combination_dna(paper_dna: dict, topic_name: str) -> dict | None:
    """Find this topic's entry in the paper_dna combination_dna array."""
    combination_dna_list = paper_dna.get("combination_dna") or []
    for entry in combination_dna_list:
        if entry.get("topic_name", "").strip().lower() == topic_name.strip().lower():
            return entry
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Internal: Agent 4 mapper signal extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_mapper_signals(
    mapper_output: dict,
    topic_id: str,
    topic_number: int,
) -> tuple[str | None, str | None, str | None]:
    """
    Extract concept_bridge, left_adjacent_topic, and right_adjacent_topic
    from the Agent 4 mapper output for this specific topic.

    Returns: (concept_bridge, left_adjacent_topic, right_adjacent_topic)

    mapper_output structure (from Agent 4 schema):
    {
      "dependency_graph": [
        {
          "topic_id": "...",
          "topic_name": "...",
          "prerequisite_topic_id": "...",
          "prerequisite_bridge": "..."
        }
      ],
      "optimised_sequence": [
        {
          "unit_id": "...",
          "sequence": ["topic_id_1", "topic_id_2", ...]
        }
      ],
      ...
    }
    """
    concept_bridge    = None
    left_adj          = None
    right_adj         = None

    # ── Concept bridge ────────────────────────────────────────────────────────
    dependency_graph = mapper_output.get("dependency_graph") or []
    for entry in dependency_graph:
        if entry.get("topic_id") == topic_id:
            concept_bridge = entry.get("prerequisite_bridge")
            break

    # ── Adjacent topics from optimised sequence ───────────────────────────────
    optimised_sequence = mapper_output.get("optimised_sequence") or []
    topic_names_by_id  = _build_topic_names_index(mapper_output)

    for unit_seq in optimised_sequence:
        seq = unit_seq.get("sequence") or []
        if topic_id in seq:
            pos = seq.index(topic_id)
            if pos > 0:
                left_id  = seq[pos - 1]
                left_adj = topic_names_by_id.get(left_id)
            if pos < len(seq) - 1:
                right_id  = seq[pos + 1]
                right_adj = topic_names_by_id.get(right_id)
            break

    return concept_bridge, left_adj, right_adj


def _build_topic_names_index(mapper_output: dict) -> dict[str, str]:
    """Build a topic_id → topic_name lookup from mapper output."""
    index: dict[str, str] = {}
    for entry in mapper_output.get("dependency_graph") or []:
        tid   = entry.get("topic_id")
        tname = entry.get("topic_name")
        if tid and tname:
            index[tid] = tname
    return index


# ─────────────────────────────────────────────────────────────────────────────
#  Internal: syllabus content extraction
# ─────────────────────────────────────────────────────────────────────────────

def _get_syllabus_content(topic_row: dict) -> list[str]:
    """
    Extract the syllabus bullet points for this topic.

    The topic_row should have a 'syllabus_content' field injected by the
    orchestrator from the Agent 2 syllabus extraction output. If absent,
    fall back to just the topic name as a single-item list.
    """
    content = topic_row.get("syllabus_content")
    if isinstance(content, list) and content:
        return content
    if isinstance(content, str) and content.strip():
        return [content.strip()]
    # Fallback: topic name only. Writer will handle it.
    return [topic_row.get("topic_name", "Unknown topic")]


# ─────────────────────────────────────────────────────────────────────────────
#  Internal: database write
# ─────────────────────────────────────────────────────────────────────────────

def _write_topic_to_db(topic_id: str, result: dict) -> None:
    """
    Write the validated topic output to the Supabase topics table.

    Maps every top-level key from the Writer output to its corresponding
    Supabase column. All JSONB columns receive the dict/list directly.
    """
    fields_to_write: dict[str, Any] = {
        # Scalar fields
        "priority":                  result.get("priority"),
        "difficulty":                result.get("difficulty"),
        "estimated_study_minutes":   result.get("estimated_study_minutes"),
        "depth_signal_source":       result.get("depth_signal_source"),
        "definition":                result.get("definition"),
        "core_concept":              result.get("core_concept"),
        "analogy":                   result.get("analogy"),
        "analogy_verified":          result.get("analogy_verified"),
        "examiners_note":            result.get("examiners_note"),
        "examiners_note_pyq_refs":   result.get("examiners_note_pyq_refs"),

        # JSONB fields
        "rapid_revision":            result.get("rapid_revision"),
        "examples":                  result.get("examples"),
        "diagram_block":             result.get("diagram_block"),
        "instruction_word_frequency": result.get("instruction_word_frequency"),
        "common_mistakes":           result.get("common_mistakes"),
        "answer_writing_technique":  result.get("answer_writing_technique"),
        "pyqs":                      result.get("pyqs"),
        "flagged_fields":            result.get("flagged_fields"),

        # Array fields
        "quick_checks":              result.get("quick_checks"),

        # Timestamp
        "generated_at": "NOW()",
        "last_updated": "NOW()",
    }

    # Remove None values — do not overwrite existing DB fields with nulls
    # UNLESS the field was explicitly set to null in the schema output.
    # The Writer sets null intentionally (e.g. diagram_block for non-diagram topics).
    # We write null for those. We just don't write keys that aren't in the output at all.
    fields_to_write = {k: v for k, v in fields_to_write.items() if k in result or k in ("generated_at", "last_updated")}

    db.table("topics").update(fields_to_write).eq("id", topic_id).execute()
    logger.debug(f"[Writer] DB write complete for topic_id={topic_id}")


# ─────────────────────────────────────────────────────────────────────────────
#  Internal: retry sleep
# ─────────────────────────────────────────────────────────────────────────────

def _sleep_before_retry(attempt: int) -> None:
    """Exponential backoff between retry attempts."""
    wait = attempt * RETRY_DELAY_SECONDS
    logger.info(f"[Writer] Waiting {wait}s before retry attempt {attempt + 1}...")
    time.sleep(wait)


# ─────────────────────────────────────────────────────────────────────────────
#  CLI: local topic test (run directly to test a single topic)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Local test runner for Phase 4 iterative tuning.

    Usage:
        python -m backend.pipeline.agents.05_writer

    This bypasses the orchestrator and database. It builds a minimal mock
    topic and runs the Writer call directly, printing the result to stdout.
    Use this to tune writer_invariant.txt until output quality is right.

    PHASE 4 TUNING INSTRUCTIONS (from Personal_Build_Phases.txt):
      1. Run this on 2 topics.
      2. Read the output critically against the 35 quality benchmark criteria
         in Technical Reference Section 6.
      3. If the output fails any criterion, edit writer_invariant.txt.
      4. Keep a comment log of what you changed and why — see TUNING_LOG below.
      5. Re-run until both topics pass all applicable benchmark criteria.
    """

    # ── TUNING_LOG ─────────────────────────────────────────────────────────────
    # Date       | Change                                          | Reason
    # -----------|------------------------------------------------|-------------------------------
    # (add entries here as you tune the invariant prompt)

    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # ── Minimal mock topic: replace with your actual test data ────────────────
    mock_topic_row = {
        "id": "test-topic-id-001",
        "upc": "BSCMT201",
        "topic_name": "Cauchy Sequences",
        "topic_number": 4,
        "split_generation": False,
        "syllabus_content": [
            "Cauchy sequences",
            "Cauchy criterion for convergence",
            "Every Cauchy sequence is bounded",
            "Completeness of the real number system",
        ],
    }

    mock_paper_row = {
        "upc": "BSCMT201",
        "paper_type": "theory",
        "diagram_heavy": False,
        "primary_textbook": "Introduction to Real Analysis — Bartle and Sherbert, 4th ed.",
        "documentation_tier": 2,
        "paper_dna": {
            "topic_dna": [
                {
                    "topic_name": "Cauchy Sequences",
                    "appearances": [
                        {"year": 2023, "marks": 6, "question_type": "prove", "unit": 1},
                        {"year": 2024, "marks": 6, "question_type": "prove", "unit": 1},
                    ],
                    "total_appearances": 2,
                    "marks_trend": "stable",
                    "priority": "high",
                    "never_asked": False,
                    "recency_weight": 1.5,
                }
            ],
            "language_dna": [
                {
                    "topic_name": "Cauchy Sequences",
                    "instruction_words": {"prove": 2, "state": 1, "define": 0, "find": 0},
                    "examiner_vocabulary": [
                        "Prove that every Cauchy sequence is bounded",
                        "State and prove the Cauchy criterion for convergence",
                    ],
                    "typical_phrasing": "Prove that every Cauchy sequence in $\\mathbb{R}$ is convergent.",
                }
            ],
            "combination_dna": [
                {
                    "topic_name": "Cauchy Sequences",
                    "always_asked_with": ["Convergent Sequences"],
                    "combination_pattern": "Prove every Cauchy sequence is convergent, hence bounded",
                    "standalone_frequency": 0.3,
                    "diagram_required": False,
                    "numerical_always": False,
                }
            ],
        },
    }

    mock_mapper_output = {
        "dependency_graph": [
            {
                "topic_id": "test-topic-id-001",
                "topic_name": "Cauchy Sequences",
                "prerequisite_topic_id": "test-topic-id-000",
                "prerequisite_bridge": (
                    "Requires: convergence of sequences. "
                    "Why: a Cauchy sequence is defined in terms of the distance between terms — "
                    "understanding convergence tells you what that distance is converging toward. "
                    "Bridge: A sequence $\\{a_n\\}$ is Cauchy if for every $\\varepsilon > 0$ "
                    "there exists $N$ such that $|a_m - a_n| < \\varepsilon$ for all $m, n > N$ — "
                    "this is the internal condition for convergence, not requiring knowledge of the limit."
                ),
            }
        ],
        "optimised_sequence": [
            {
                "unit_id": "unit-001",
                "sequence": ["test-topic-id-000", "test-topic-id-001", "test-topic-id-002"],
            }
        ],
    }

    # ── Run the Writer ────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("STUDYAI WRITER — PHASE 4 LOCAL TEST")
    print("="*60)
    print(f"Topic: {mock_topic_row['topic_name']}")
    print(f"UPC:   {mock_topic_row['upc']}")
    print("="*60 + "\n")

    # Bypass DB writes for local testing
    def _noop_update_status(tid, status): print(f"[mock DB] status → {status}")
    def _noop_write_fields(tid, fields): print(f"[mock DB] writing {len(fields)} fields")

    import unittest.mock as mock
    with mock.patch("backend.pipeline.agents.05_writer.update_topic_status", _noop_update_status), \
         mock.patch("backend.pipeline.agents.05_writer.write_topic_fields", _noop_write_fields), \
         mock.patch("backend.pipeline.agents.05_writer.auto_fix_latex", lambda x: x):

        result = run_writer(
            topic_row=mock_topic_row,
            unit_row={},
            paper_row=mock_paper_row,
            mapper_output=mock_mapper_output,
        )

    print("\n" + "="*60)
    if result:
        print("✓ Writer succeeded. Output:\n")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("\n" + "="*60)
        print("PHASE 4 QUALITY CHECKLIST — run through these manually:")
        print("  [ ] definition under 40 words?")
        print("  [ ] all LaTeX correct (no raw unicode symbols)?")
        print("  [ ] rapid_revision.definition_one_line under 15 words?")
        print("  [ ] examiners_note references a specific PYQ year?")
        print("  [ ] examiners_note uses exact instruction word from Language DNA?")
        print("  [ ] quick_checks has exactly 3 items with no answers?")
        print("  [ ] common_mistakes specific to DU (not generic advice)?")
        print("  [ ] answer_writing_technique present (6-mark topic)?")
        print("  [ ] No filler phrases ('important to note', 'crucial role')?")
        print("="*60)
    else:
        print("✗ Writer failed after all retries. Check logs above.")
        print("="*60)

async def run(topic: dict, paper: dict, cost=None, split_mode=None) -> dict:
    from database import queries as q
    import asyncio
    unit_id = topic.get("unit_id")
    unit_row: dict = {}
    if unit_id:
        units = q.get_units_for_paper(paper["upc"])
        unit_row = next((u for u in units if u["id"] == unit_id), {})
    mapper_output = paper.get("_mapper_output") or {}
    return await asyncio.to_thread(run_writer, topic, unit_row, paper, mapper_output)
