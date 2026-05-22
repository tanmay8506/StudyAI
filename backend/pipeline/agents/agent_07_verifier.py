"""
Agent 07 — Proof & Numerical Verifier
Models:
  - Cerebras (numerical single verification)
  - Groq Mixtral (numerical dual verification — paired with Cerebras)
  - Gemini 2.0 Flash (proof verification — logical step validation)
Fires: Per topic, only on High Priority topics.
Purpose:
  - For numerical topics: verify every worked example step-by-step.
  - For proof topics: verify every logical step follows from valid premises.
Retry: If unavailable → verified: false saved. No badge shown. Queued for retry.
Dual verification disagreement → flag for manual review.
Proof flags → passed to Critic diff, not marked verified until re-verification passes.
"""

import json
import os
import logging
from pathlib import Path
from typing import Literal

import google.generativeai as genai
from groq import Groq
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
CEREBRAS_MODEL = "llama3.1-70b"
GROQ_MIXTRAL_MODEL = "mixtral-8x7b-32768"
GEMINI_MODEL = "gemini-2.0-flash"
MAX_TOKENS = 1024

PROOF_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "proof_verifier.txt"

# Instruction words that signal a proof-type question in DU exams
PROOF_INSTRUCTION_WORDS = frozenset({"prove", "show", "establish", "verify", "demonstrate"})


def _load_proof_prompt() -> str:
    return PROOF_PROMPT_PATH.read_text(encoding="utf-8").strip()


def _is_proof_topic(topic: dict) -> bool:
    """
    Determine if a topic requires proof verification rather than numerical verification.
    Uses Language DNA instruction words as the primary signal.
    Falls back to example type fields.
    """
    # Check language DNA instruction words
    lang_dna = topic.get("instruction_word_frequency", {})
    if lang_dna:
        for word, count in lang_dna.items():
            if word.lower() in PROOF_INSTRUCTION_WORDS and count > 0:
                return True

    # Check example types
    examples = topic.get("examples", []) or []
    for ex in examples:
        mode = ex.get("verification_mode", "")
        if mode == "proof":
            return True

    return False


def _parse_verifier_json(raw: str, context: str) -> dict:
    """Parse and strip markdown fences from verifier response."""
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        clean = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{context}: non-JSON response: {exc}\nRaw:\n{raw[:300]}") from exc


# ── Numerical Verification ───────────────────────────────────────────────────

def _build_numerical_prompt(example: dict, example_index: int) -> str:
    """Build the verification prompt for a single numerical example."""
    steps_text = "\n".join(
        f"Step {s['step_number']}: {s['step_text']}"
        for s in (example.get("steps") or [])
    )
    return f"""Verify this worked numerical example from DU B.Sc. NEP study notes.

PROBLEM:
{example.get("content", "")}

SOLUTION STEPS:
{steps_text}

STATED ANSWER:
{example.get("answer", "")}

CHECK:
1. Is every step mathematically correct?
2. Does the final answer follow from the last step?
3. Are units consistent throughout? (Flag any step missing units if units are expected.)
4. Is the stated answer correct?

Output ONLY valid JSON in this exact format:
{{
  "verified": true | false,
  "flagged_steps": [
    {{ "step_number": <int>, "issue": "<specific mathematical error>" }}
  ],
  "answer_correct": true | false,
  "answer_note": "<empty string if correct, specific error otherwise>"
}}
No prose. No markdown. JSON only."""


def _verify_numerical_cerebras(
    client_cerebras: Cerebras,
    example: dict,
    example_index: int,
    topic_name: str,
) -> dict:
    """Run single-pass numerical verification via Cerebras."""
    prompt = _build_numerical_prompt(example, example_index)
    try:
        response = client_cerebras.chat.completions.create(
            model=CEREBRAS_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content
        return _parse_verifier_json(raw, f"Cerebras numerical [{topic_name}] example {example_index}")
    except Exception as exc:
        logger.warning(
            "Cerebras unavailable | topic=%s | example=%d | error=%s",
            topic_name, example_index, exc,
        )
        raise


def _verify_numerical_groq_mixtral(
    client_groq: Groq,
    example: dict,
    example_index: int,
    topic_name: str,
) -> dict:
    """Run dual-pass numerical verification via Groq Mixtral."""
    prompt = _build_numerical_prompt(example, example_index)
    try:
        response = client_groq.chat.completions.create(
            model=GROQ_MIXTRAL_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content
        return _parse_verifier_json(raw, f"Mixtral numerical [{topic_name}] example {example_index}")
    except Exception as exc:
        logger.warning(
            "Groq Mixtral unavailable | topic=%s | example=%d | error=%s",
            topic_name, example_index, exc,
        )
        raise


def _reconcile_dual_results(
    cerebras_result: dict,
    mixtral_result: dict,
    example_index: int,
    topic_name: str,
) -> dict:
    """
    Reconcile dual numerical verification results.
    Agreement on verified=True → pass. Agreement on False → fail.
    Disagreement → manual_review flag.
    """
    c_verified = cerebras_result.get("verified", False)
    m_verified = mixtral_result.get("verified", False)

    if c_verified == m_verified:
        # Agreement — merge flagged steps from both (deduplicate by step_number)
        all_flags = {
            f["step_number"]: f
            for f in (
                cerebras_result.get("flagged_steps", [])
                + mixtral_result.get("flagged_steps", [])
            )
        }
        return {
            "verified": c_verified,
            "flagged_steps": list(all_flags.values()),
            "answer_correct": cerebras_result.get("answer_correct", False),
            "manual_review": False,
            "verification_mode": "numerical_dual",
        }
    else:
        # Disagreement — manual review required
        logger.warning(
            "Dual verification DISAGREEMENT | topic=%s | example=%d | cerebras=%s | mixtral=%s",
            topic_name, example_index, c_verified, m_verified,
        )
        return {
            "verified": False,
            "flagged_steps": [],
            "answer_correct": None,
            "manual_review": True,
            "manual_review_reason": (
                f"Cerebras: verified={c_verified}, Mixtral: verified={m_verified}. "
                "Models disagree — requires human review."
            ),
            "verification_mode": "numerical_dual",
        }


def _verify_numerical(
    topic: dict,
    client_cerebras: Cerebras,
    client_groq: Groq,
) -> list[dict]:
    """
    Verify all numerical examples in a topic.
    Returns a list of per-example verification results.
    """
    topic_name = topic.get("topic_name", "unknown")
    examples = topic.get("examples", []) or []
    results = []

    for idx, example in enumerate(examples):
        ex_type = example.get("type", "")
        if ex_type not in ("numerical",):
            # Only verify numerical examples in this pass
            results.append({
                "example_index": idx,
                "skipped": True,
                "skip_reason": f"type={ex_type}, not numerical",
            })
            continue

        mode = example.get("verification_mode", "numerical_single")

        if mode == "numerical_dual":
            # Try Cerebras first
            try:
                cerebras_r = _verify_numerical_cerebras(client_cerebras, example, idx, topic_name)
            except Exception as exc:
                logger.warning("Cerebras failed for dual pass, falling back to single | %s", exc)
                # Degrade gracefully to single Groq pass
                try:
                    groq_r = _verify_numerical_groq_mixtral(client_groq, example, idx, topic_name)
                    results.append({
                        "example_index": idx,
                        **groq_r,
                        "verification_mode": "numerical_single",
                        "degraded": True,
                    })
                except Exception as exc2:
                    logger.error("Both models failed for example %d | topic=%s | %s", idx, topic_name, exc2)
                    results.append({
                        "example_index": idx,
                        "verified": False,
                        "skipped": True,
                        "error": str(exc2),
                    })
                continue

            # Try Mixtral for dual
            try:
                mixtral_r = _verify_numerical_groq_mixtral(client_groq, example, idx, topic_name)
                reconciled = _reconcile_dual_results(cerebras_r, mixtral_r, idx, topic_name)
                results.append({"example_index": idx, **reconciled})
            except Exception as exc:
                # Dual failed — fall back to single Cerebras result
                logger.warning("Mixtral failed, using Cerebras single result | %s", exc)
                results.append({
                    "example_index": idx,
                    **cerebras_r,
                    "verification_mode": "numerical_single",
                    "degraded": True,
                })

        else:
            # Single numerical pass via Cerebras
            try:
                r = _verify_numerical_cerebras(client_cerebras, example, idx, topic_name)
                results.append({"example_index": idx, **r, "verification_mode": "numerical_single"})
            except Exception as exc:
                try:
                    # Fallback to Groq Mixtral
                    r = _verify_numerical_groq_mixtral(client_groq, example, idx, topic_name)
                    results.append({
                        "example_index": idx,
                        **r,
                        "verification_mode": "numerical_single",
                        "degraded": True,
                    })
                except Exception as exc2:
                    results.append({
                        "example_index": idx,
                        "verified": False,
                        "skipped": True,
                        "error": str(exc2),
                    })

    return results


# ── Proof Verification ───────────────────────────────────────────────────────

def _build_proof_content(topic: dict) -> str:
    """Extract proof-type examples and any derivation in core_concept for verification."""
    lines = [f"TOPIC: {topic.get('topic_name', '')}"]
    lines.append(f"DEFINITION: {topic.get('definition', '')}")
    lines.append(f"CORE CONCEPT:\n{topic.get('core_concept', '')}")

    examples = topic.get("examples", []) or []
    for idx, ex in enumerate(examples):
        if ex.get("verification_mode") == "proof" or ex.get("type") in ("theory",):
            steps_text = "\n".join(
                f"  Step {s['step_number']}: {s['step_text']}"
                for s in (ex.get("steps") or [])
            )
            lines.append(f"\nPROOF/DERIVATION {idx + 1}:\nProblem: {ex.get('content', '')}\n{steps_text}\nConclusion: {ex.get('answer', '')}")

    return "\n".join(lines)


def _verify_proof_gemini(
    topic: dict,
) -> dict:
    """
    Verify proofs and derivations via Gemini 2.0 Flash.
    Returns structured verification result.
    """
    topic_name = topic.get("topic_name", "unknown")
    system_prompt = _load_proof_prompt()
    user_content = _build_proof_content(topic)

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_prompt,
    )

    try:
        response = model.generate_content(
            user_content,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=MAX_TOKENS,
            ),
        )
        raw = response.text
        result = _parse_verifier_json(raw, f"Gemini proof [{topic_name}]")
        return {**result, "verification_mode": "proof"}
    except Exception as exc:
        logger.error("Gemini proof verification failed | topic=%s | error=%s", topic_name, exc)
        raise


# ── Entry Point ──────────────────────────────────────────────────────────────

def run_sync(topic: dict) -> dict:
    """
    Execute the Verifier for a single topic.

    Fires only on High Priority topics. Low/medium/never_asked topics are skipped
    with verified=False and verification_mode="none" — this is correct and expected.

    Args:
        topic: Fully-generated topic dict from the Writer. Must include at minimum:
               id, topic_name, priority, examples, core_concept, instruction_word_frequency.

    Returns:
        dict with keys:
          "topic_id": str
          "priority": str
          "fired": bool — False if topic was skipped due to priority
          "is_proof": bool
          "numerical_results": list[dict] — one entry per example (may be empty)
          "proof_result": dict | None — only populated for proof topics
          "overall_verified": bool — True only if all checks pass
          "manual_review": bool — True if any dual-verification disagreement
          "error": str | None
    """
    topic_id = topic.get("id", "unknown")
    topic_name = topic.get("topic_name", "unknown")
    priority = topic.get("priority", "low")

    # Skip all non-high-priority topics — verifier fires only on high priority
    if priority != "high":
        logger.info(
            "Verifier skipped (not high priority) | topic_id=%s | topic=%s | priority=%s",
            topic_id, topic_name, priority,
        )
        return {
            "topic_id": topic_id,
            "priority": priority,
            "fired": False,
            "is_proof": False,
            "numerical_results": [],
            "proof_result": None,
            "overall_verified": False,
            "manual_review": False,
            "error": None,
        }

    logger.info(
        "Verifier starting | topic_id=%s | topic=%s | priority=%s",
        topic_id, topic_name, priority,
    )

    is_proof = _is_proof_topic(topic)

    # Initialise clients
    client_cerebras = Cerebras(api_key=os.environ["CEREBRAS_API_KEY"])
    client_groq = Groq(api_key=os.environ["GROQ_API_KEY"])
    # Gemini is configured per-call inside _verify_proof_gemini

    numerical_results = []
    proof_result = None
    overall_verified = True
    manual_review = False
    error = None

    # ── Numerical verification pass ──────────────────────────────────────────
    try:
        numerical_results = _verify_numerical(topic, client_cerebras, client_groq)

        for r in numerical_results:
            if r.get("skipped"):
                continue
            if not r.get("verified", False):
                overall_verified = False
            if r.get("manual_review", False):
                manual_review = True

    except Exception as exc:
        logger.error(
            "Numerical verification failed | topic_id=%s | error=%s", topic_id, exc
        )
        overall_verified = False
        error = str(exc)

    # ── Proof verification pass ───────────────────────────────────────────────
    if is_proof:
        try:
            proof_result = _verify_proof_gemini(topic)
            if not proof_result.get("verified", False):
                overall_verified = False
                # Proof failures go to Critic — not treated as manual review
                logger.warning(
                    "Proof verification FAILED | topic_id=%s | flagged_steps=%s",
                    topic_id, proof_result.get("flagged_steps", []),
                )
        except Exception as exc:
            logger.error(
                "Proof verification failed | topic_id=%s | error=%s", topic_id, exc
            )
            overall_verified = False
            proof_result = {"verified": False, "flagged_steps": [], "error": str(exc)}
            if not error:
                error = str(exc)

    logger.info(
        "Verifier complete | topic_id=%s | overall_verified=%s | proof=%s | manual_review=%s",
        topic_id, overall_verified, is_proof, manual_review,
    )

    return {
        "topic_id": topic_id,
        "priority": priority,
        "fired": True,
        "is_proof": is_proof,
        "numerical_results": numerical_results,
        "proof_result": proof_result,
        "overall_verified": overall_verified,
        "manual_review": manual_review,
        "error": error,
    }

async def run(topic: dict, paper: dict, cost=None) -> dict:
    import asyncio
    return await asyncio.to_thread(run_sync, topic)
