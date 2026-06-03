"""
Agent 08 — Critic
Model: Claude Sonnet (claude-sonnet-4-20250514)
Runs: Per topic, after Coverage Checker and Verifier complete.
Purpose:
  Field-level critique of every generated topic against DU-specific quality standards.
  Output is surgical JSON diffs ONLY — no prose, no summaries, no general observations.
  Every correction names exact field path, specific issue, and specific correction.
  Maximum 10 corrections per topic — if more exist, prioritise by marks impact.
Input:
  - The full generated topic dict from the Writer.
  - Coverage Checker flags for this unit (context only — not the source of corrections).
  - Verifier result for this topic (proof flags become Critic diffs).
Output:
  - Valid JSON matching critic_diff_schema.json exactly.
Retry: Max 2 retries if diff schema fails validation.
"""

import json
import os
import logging
from pathlib import Path

import google.generativeai as genai
import jsonschema
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.0-flash"
MAX_TOKENS = 2048
MAX_RETRIES = 2

CRITIC_CONSTITUTION_PATH = (
    Path(__file__).resolve().parents[1] / "prompts" / "critic_constitution.txt"
)
CRITIC_DIFF_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas" / "critic_diff_schema.json"
)


def _load_constitution() -> str:
    return CRITIC_CONSTITUTION_PATH.read_text(encoding="utf-8").strip()


def _load_diff_schema() -> dict:
    return json.loads(CRITIC_DIFF_SCHEMA_PATH.read_text(encoding="utf-8"))


def _build_system_prompt(constitution: str) -> str:
    """
    Assemble the full system prompt for the Critic.
    The constitution IS the system prompt — no wrapping needed.
    We append the output schema as a reminder at the end.
    """
    schema_reminder = """
━━ OUTPUT SCHEMA REMINDER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You MUST output valid JSON matching this exact schema:
{
  "topic_id": "<string>",
  "corrections": [
    {
      "field": "<exact field path, e.g. definition or examples[0].steps[2].units_shown>",
      "issue": "<specific description of what is wrong>",
      "correction": "<specific instruction for what to change>",
      "severity": "<critical | major | minor>"
    }
  ]
}
Maximum 10 corrections. Ordered by severity descending (critical first).
Output ONLY valid JSON. Do NOT include any comments (like '// ...') inside the JSON output. If there are no corrections, the 'corrections' array must be completely empty: []. No prose before or after. No markdown fences.
"""
    return f"{constitution}\n\n{schema_reminder}"


def _build_user_message(
    topic: dict,
    coverage_flags: dict | None,
    verifier_result: dict | None,
) -> str:
    """
    Build the user message for the Critic.

    Args:
        topic: Full generated topic dict.
        coverage_flags: Output from Agent 6 for this topic's unit (context only).
        verifier_result: Output from Agent 7 for this specific topic.
    Returns:
        Formatted string.
    """
    lines = ["TOPIC TO CRITIQUE:"]
    lines.append(json.dumps(topic, indent=2, ensure_ascii=False))

    if coverage_flags and not coverage_flags.get("skipped"):
        # Include coverage flags as additional context — not as a source of required corrections
        missing = [
            m for m in coverage_flags.get("missing_topics", [])
            if m.get("closest_match") == topic.get("topic_name")
               or m.get("closest_match") is None
        ]
        if missing:
            lines.append("\n━━ COVERAGE CHECKER FLAGS (context only) ━━")
            lines.append("These syllabus entries may not be covered by this topic's definition/core_concept:")
            for item in missing:
                lines.append(f"  - Syllabus entry: {item['syllabus_entry']}")

    if verifier_result and verifier_result.get("fired"):
        lines.append("\n━━ VERIFIER FLAGS ━━")
        proof_result = verifier_result.get("proof_result")
        if proof_result and not proof_result.get("verified", True):
            lines.append("PROOF VERIFICATION FAILED. The following steps were flagged:")
            for step in proof_result.get("flagged_steps", []):
                lines.append(f"  - Step {step['step_number']}: {step['issue']}")
            lines.append(
                "You MUST include a correction for each flagged proof step above. "
                "Field path: examples[<index>].steps[<step_number - 1>].step_text"
            )

        for num_r in verifier_result.get("numerical_results", []):
            if not num_r.get("verified", True) and not num_r.get("skipped"):
                ex_idx = num_r.get("example_index", 0)
                lines.append(f"\nNUMERICAL EXAMPLE {ex_idx} FAILED verification:")
                for step in num_r.get("flagged_steps", []):
                    lines.append(f"  - Step {step['step_number']}: {step['issue']}")
                if not num_r.get("answer_correct", True):
                    lines.append(f"  - FINAL ANSWER INCORRECT: {num_r.get('answer_note', '')}")
                lines.append(
                    f"You MUST include corrections for examples[{ex_idx}] fields above."
                )

    lines.append(
        f"\nOutput the critic_diff_schema.json JSON now with topic_id = \"{topic.get('id', '')}\"."
    )

    return "\n".join(lines)


def _validate_diff_output(data: dict, schema: dict, topic_id: str) -> None:
    """
    Validate the Critic output against critic_diff_schema.json.
    Raises jsonschema.ValidationError on failure.
    """
    jsonschema.validate(instance=data, schema=schema)

    # Extra: ensure topic_id in output matches expected
    if data.get("topic_id") != topic_id:
        raise ValueError(
            f"Critic output topic_id mismatch: expected '{topic_id}', got '{data.get('topic_id')}'"
        )

    # Extra: ensure severity values are valid
    valid_severities = {"critical", "major", "minor"}
    for correction in data.get("corrections", []):
        sev = correction.get("severity", "")
        if sev not in valid_severities:
            raise ValueError(f"Invalid severity '{sev}' in correction: {correction}")


def _parse_raw_output(raw: str) -> dict:
    """Strip markdown fences and parse JSON."""
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        clean = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()
    return json.loads(clean)


def run_sync(
    topic: dict,
    coverage_flags: dict | None = None,
    verifier_result: dict | None = None,
) -> dict:
    """
    Execute the Critic for a single topic.

    Args:
        topic: Fully-generated topic dict from the Writer. Must include at minimum:
               id, topic_name, and all fields that the constitution checks.
        coverage_flags: Output from Agent 6 run() for the parent unit.
                        Passed as context — not as a directive.
        verifier_result: Output from Agent 7 run() for this topic.
                         Proof failures and numerical failures are injected into the
                         user message as mandatory correction targets.

    Returns:
        dict with keys:
          "topic_id": str
          "corrections": list[dict]   — validated diff items (may be empty if notes are perfect)
          "correction_count": int
          "critical_count": int
          "major_count": int
          "minor_count": int
          "retry_count": int
          "failed": bool  — True only if all retries exhausted without valid output
          "error": str | None
    """
    topic_id = topic.get("id", "unknown")
    topic_name = topic.get("topic_name", "unknown")

    constitution = _load_constitution()
    diff_schema = _load_diff_schema()
    system_prompt = _build_system_prompt(constitution)
    user_message = _build_user_message(topic, coverage_flags, verifier_result)

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    logger.info(
        "Critic starting | topic_id=%s | topic=%s",
        topic_id, topic_name,
    )

    last_error = None

    for attempt in range(MAX_RETRIES + 1):  # attempt 0, 1, 2
        if attempt > 0:
            logger.warning(
                "Critic retry %d/%d | topic_id=%s | previous_error=%s",
                attempt, MAX_RETRIES, topic_id, last_error,
            )

        # On retry, inject a schema enforcement reminder into the user message
        retry_suffix = ""
        if attempt > 0:
            retry_suffix = (
                f"\n\nPREVIOUS ATTEMPT FAILED SCHEMA VALIDATION: {last_error}\n"
                "You MUST output valid JSON matching critic_diff_schema.json exactly. "
                "Corrections array must be present. No prose. No markdown."
            )

        try:
            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=system_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=MAX_TOKENS,
                    response_mime_type="application/json",
                )
            )
            response = model.generate_content(user_message + retry_suffix)
            raw_output = response.text
        except Exception as exc:
            last_error = str(exc)
            logger.error(
                "Critic API error | topic_id=%s | attempt=%d | error=%s",
                topic_id, attempt, exc,
            )
            continue

        try:
            data = _parse_raw_output(raw_output)
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = f"JSON parse error: {exc}"
            logger.warning(
                "Critic output parse failed | topic_id=%s | attempt=%d | error=%s | raw_output=%r",
                topic_id, attempt, exc, raw_output,
            )
            continue

        try:
            _validate_diff_output(data, diff_schema, topic_id)
        except (jsonschema.ValidationError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "Critic output schema validation failed | topic_id=%s | attempt=%d | error=%s",
                topic_id, attempt, exc,
            )
            continue

        # ── Success ──────────────────────────────────────────────────────────
        corrections = data.get("corrections", [])

        # Sort: critical first, then major, then minor
        severity_order = {"critical": 0, "major": 1, "minor": 2}
        corrections.sort(key=lambda c: severity_order.get(c.get("severity", "minor"), 2))

        critical_count = sum(1 for c in corrections if c.get("severity") == "critical")
        major_count = sum(1 for c in corrections if c.get("severity") == "major")
        minor_count = sum(1 for c in corrections if c.get("severity") == "minor")

        logger.info(
            "Critic complete | topic_id=%s | topic=%s | total=%d "
            "(critical=%d, major=%d, minor=%d) | attempts=%d",
            topic_id, topic_name,
            len(corrections), critical_count, major_count, minor_count,
            attempt + 1,
        )

        for corr in corrections:
            logger.debug(
                "CORRECTION [%s] | topic_id=%s | field=%s | issue=%s",
                corr["severity"].upper(), topic_id, corr["field"], corr["issue"][:80],
            )

        return {
            "topic_id": topic_id,
            "corrections": corrections,
            "correction_count": len(corrections),
            "critical_count": critical_count,
            "major_count": major_count,
            "minor_count": minor_count,
            "retry_count": attempt,
            "failed": False,
            "error": None,
        }

    # All retries exhausted
    logger.error(
        "Critic FAILED after %d attempts | topic_id=%s | last_error=%s",
        MAX_RETRIES + 1, topic_id, last_error,
    )
    return {
        "topic_id": topic_id,
        "corrections": [],
        "correction_count": 0,
        "critical_count": 0,
        "major_count": 0,
        "minor_count": 0,
        "retry_count": MAX_RETRIES,
        "failed": True,
        "error": last_error,
    }

async def run(topic: dict, paper: dict, verify_result: dict, coverage_flags: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_sync, topic, coverage_flags, verify_result)
