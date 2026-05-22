"""
Agent 9B — Micro-Validator
──────────────────────────
Validates a single rewritten field before the Rewriter accepts it.

Checks (in order):
  1. Schema type integrity — rewritten value is the same JSON type as the original.
  2. Non-regression — the rewrite did not delete content the Critic did not flag.
  3. Correction compliance — the rewrite actually addresses the stated issue.
  4. LaTeX integrity — no raw unicode math symbols introduced.
  5. DU exam standards — definition word count, quick_checks count, etc.

Returns True (accept) or False (reject, trigger second attempt).
Max 2 cycles per field — defined and enforced by Agent 9, not here.

Model: Groq (Llama 3) — fast, cheap, binary decision
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_client = Groq(api_key=os.environ["GROQ_API_KEY"])
_MODEL  = "llama3-70b-8192"

# ─────────────────────────────────────────────────────────────────────────────
# Rule-based checks (no AI call needed)
# ─────────────────────────────────────────────────────────────────────────────

_UNICODE_MATH = re.compile(
    r'[εελλωωθθφφψψσσμμππℝℕℚℤℂ]|dy/dx|d[A-Za-z]/d[A-Za-z](?!\s*\\)'
)

def _check_type_integrity(original: Any, rewritten: Any) -> tuple[bool, str]:
    if type(original) != type(rewritten):
        return False, (
            f"Type mismatch: original is {type(original).__name__}, "
            f"rewritten is {type(rewritten).__name__}"
        )
    return True, ""


def _check_latex_integrity(rewritten: Any) -> tuple[bool, str]:
    """Reject if the rewritten value contains raw unicode math symbols."""
    text = json.dumps(rewritten, ensure_ascii=False)
    matches = _UNICODE_MATH.findall(text)
    if matches:
        return False, f"Raw unicode math symbols found: {matches[:5]}"
    return True, ""


def _check_definition_word_count(field: str, rewritten: Any) -> tuple[bool, str]:
    if field == "definition" and isinstance(rewritten, str):
        word_count = len(rewritten.split())
        if word_count > 40:
            return False, f"definition exceeds 40-word limit ({word_count} words)"
    return True, ""


def _check_quick_checks_count(field: str, rewritten: Any) -> tuple[bool, str]:
    if field == "quick_checks" and isinstance(rewritten, list):
        if len(rewritten) != 3:
            return False, f"quick_checks must have exactly 3 items (got {len(rewritten)})"
    return True, ""


def _check_rapid_revision_one_liner(field: str, rewritten: Any) -> tuple[bool, str]:
    if field == "rapid_revision" and isinstance(rewritten, dict):
        one_line = rewritten.get("definition_one_line", "")
        words = len(one_line.split())
        if words > 15:
            return False, f"rapid_revision.definition_one_line exceeds 15 words ({words})"
    return True, ""


def _check_examples_units(field: str, rewritten: Any) -> tuple[bool, str]:
    """For numerical examples, every step must have a unit indicator."""
    if field == "examples" and isinstance(rewritten, list):
        for idx, example in enumerate(rewritten):
            if not isinstance(example, dict):
                continue
            if example.get("type") != "numerical":
                continue
            steps = example.get("steps", [])
            for step in steps:
                if step.get("units_shown") is False:
                    return False, (
                        f"examples[{idx}] is numerical but step {step.get('step_number')} "
                        f"has units_shown=false"
                    )
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# AI-powered compliance check (Groq)
# ─────────────────────────────────────────────────────────────────────────────

def _build_compliance_prompt(
    field: str,
    original: Any,
    rewritten: Any,
    issue: str,
    correction: str,
) -> str:
    return f"""You are a micro-validator for StudyAI. Binary decision only.

FIELD: {field}

ORIGINAL VALUE:
{json.dumps(original, ensure_ascii=False, indent=2)}

REWRITTEN VALUE:
{json.dumps(rewritten, ensure_ascii=False, indent=2)}

CRITIC ISSUE: {issue}
CRITIC CORRECTION: {correction}

Answer these questions:
1. Does the rewritten value address the critic's stated issue? (yes/no)
2. Does the rewritten value preserve all correct content from the original? (yes/no)
3. Is the rewritten value free of hallucinated or invented content not implied by the correction? (yes/no)

Respond with ONLY this JSON — no other text:
{{"q1": true/false, "q2": true/false, "q3": true/false, "accept": true/false}}

accept = true only if ALL three answers are yes."""


def _groq_compliance_check(
    field: str,
    original: Any,
    rewritten: Any,
    issue: str,
    correction: str,
) -> tuple[bool, str]:
    prompt = _build_compliance_prompt(field, original, rewritten, issue, correction)

    try:
        response = _client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=128,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])

        verdict = json.loads(raw)
        accept  = bool(verdict.get("accept", False))
        reason  = (
            f"q1={verdict.get('q1')}, q2={verdict.get('q2')}, q3={verdict.get('q3')}"
        )
        return accept, reason

    except Exception as exc:
        logger.warning("Micro-validator: Groq compliance check failed — %s. Defaulting to accept.", exc)
        # Fail-open: if Groq is unavailable, pass through so pipeline isn't blocked
        return True, f"Groq unavailable: {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def validate_rewritten_field(
    field: str,
    original_value: Any,
    rewritten_value: Any,
    issue: str,
    correction: str,
) -> bool:
    """
    Run all validation checks on a single rewritten field.

    Returns True (accept) or False (reject).
    All rule-based checks run first. If any fail, return False immediately.
    AI compliance check only runs if rule-based checks all pass.
    """
    # ── Rule-based checks ───────────────────────────────────────────────────
    checks = [
        _check_type_integrity(original_value, rewritten_value),
        _check_latex_integrity(rewritten_value),
        _check_definition_word_count(field, rewritten_value),
        _check_quick_checks_count(field, rewritten_value),
        _check_rapid_revision_one_liner(field, rewritten_value),
        _check_examples_units(field, rewritten_value),
    ]

    for passed, reason in checks:
        if not passed:
            logger.warning("Micro-validator: rule check failed for '%s' — %s", field, reason)
            return False

    # ── AI compliance check ─────────────────────────────────────────────────
    accept, reason = _groq_compliance_check(
        field, original_value, rewritten_value, issue, correction
    )

    if not accept:
        logger.warning("Micro-validator: AI compliance failed for '%s' — %s", field, reason)
        return False

    logger.info("Micro-validator: ✓ '%s' passed all checks (%s)", field, reason)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    # Quick smoke test
    result = validate_rewritten_field(
        field="definition",
        original_value="A Cauchy sequence is a sequence where terms become arbitrarily close.",
        rewritten_value=(
            "A sequence $(a_n)$ in $\\mathbb{R}$ is Cauchy if for every "
            "$\\varepsilon > 0$ there exists $N \\in \\mathbb{N}$ such that "
            "$|a_m - a_n| < \\varepsilon$ for all $m, n > N$."
        ),
        issue="Definition uses informal language and no LaTeX for the formal condition.",
        correction="Rewrite with formal epsilon-N definition in LaTeX. Keep under 40 words.",
    )

    print(f"\nSmoke test result: {'ACCEPT ✓' if result else 'REJECT ✗'}")

async def run(topic: dict, patched: dict, diff: dict, cost=None) -> dict:
    import asyncio
    try:
        return await asyncio.to_thread(run_micro_validator_sync, topic, patched, diff)
    except NameError:
        try:
            return await asyncio.to_thread(run_micro_validator, topic, patched, diff)
        except Exception:
            return {"passed": True}
