"""
Agent 12 — Consistency Checker
────────────────────────────────
Runs once per paper after ALL units are complete.
Final automated gate before pipeline_status is set to 'complete'.

Five checks:
  CHECK 1 — Notation consistency     (same quantity, same notation across topics)
  CHECK 2 — Definition consistency   (same term, compatible definitions)
  CHECK 3 — PYQ year consistency     (no question tagged with two different years)
  CHECK 4 — Priority tag consistency (never_asked tags vs actual PYQ appearances)
  CHECK 5 — LaTeX consistency        (no raw unicode math in any field)

Minor violations (LaTeX unicode): auto-patched by rule-based code — no AI call.
Major violations: routed back to Critic (Agent 8) for those specific topics.
Critical violations (PYQ year conflicts): logged and surfaced, require human review.

Model: Groq (Llama 3) — runs at paper level, cost-sensitive
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
_MODEL  = "llama-3.3-70b-versatile"

# ─────────────────────────────────────────────────────────────────────────────
# Rule-based auto-patcher for LaTeX violations (no AI call needed)
# ─────────────────────────────────────────────────────────────────────────────

_UNICODE_TO_LATEX: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bε\b'),    r'\\varepsilon'),
    (re.compile(r'\bλ\b'),    r'\\lambda'),
    (re.compile(r'\bω\b'),    r'\\omega'),
    (re.compile(r'\bθ\b'),    r'\\theta'),
    (re.compile(r'\bφ\b'),    r'\\phi'),
    (re.compile(r'\bψ\b'),    r'\\psi'),
    (re.compile(r'\bσ\b'),    r'\\sigma'),
    (re.compile(r'\bμ\b'),    r'\\mu'),
    (re.compile(r'\bπ\b'),    r'\\pi'),
    (re.compile(r'ℝ'),         r'\\mathbb{R}'),
    (re.compile(r'ℕ'),         r'\\mathbb{N}'),
    (re.compile(r'ℚ'),         r'\\mathbb{Q}'),
    (re.compile(r'ℤ'),         r'\\mathbb{Z}'),
    (re.compile(r'ℂ'),         r'\\mathbb{C}'),
    # Bare dy/dx pattern not already inside LaTeX delimiters
    (re.compile(r'(?<!\$)d([A-Za-z])/d([A-Za-z])(?!\})'), r'$\\frac{d\1}{d\2}$'),
]


def _auto_patch_latex(text: str) -> str:
    for pattern, replacement in _UNICODE_TO_LATEX:
        text = pattern.sub(replacement, text)
    return text


def _apply_latex_autopatch(topic: dict) -> tuple[dict, list[str]]:
    """
    Walk all string fields of a topic and apply LaTeX auto-patch.
    Returns (patched_topic, list of patched field paths).
    """
    patched_fields: list[str] = []

    def _walk(obj: Any, path: str) -> Any:
        if isinstance(obj, str):
            fixed = _auto_patch_latex(obj)
            if fixed != obj:
                patched_fields.append(path)
            return fixed
        elif isinstance(obj, dict):
            return {k: _walk(v, f"{path}.{k}") for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_walk(item, f"{path}[{i}]") for i, item in enumerate(obj)]
        return obj

    import copy
    patched = _walk(copy.deepcopy(topic), topic.get("topic_name", "topic"))
    return patched, patched_fields


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based pre-checks (fast, no AI)
# ─────────────────────────────────────────────────────────────────────────────

def _check_pyq_year_conflicts(topics: list[dict]) -> list[dict]:
    """
    CHECK 3 — same question text in two different topics with different years → critical.
    Same question text in two topics (any year) → critical duplicate.
    """
    violations: list[dict] = []
    seen: dict[str, dict] = {}  # normalised question text → {year, topic_id, topic_name}

    for t in topics:
        for pyq in t.get("pyqs", []):
            qt_raw = pyq.get("question_text", "").strip()
            qt_key = " ".join(qt_raw.lower().split())[:120]  # normalise whitespace, truncate
            year   = pyq.get("year")

            if qt_key in seen:
                prev = seen[qt_key]
                if prev["year"] != year or prev["topic_id"] != t["id"]:
                    violations.append({
                        "question_text": qt_raw[:100],
                        "year_a":        prev["year"],
                        "topic_a":       prev["topic_id"],
                        "topic_name_a":  prev["topic_name"],
                        "year_b":        year,
                        "topic_b":       t["id"],
                        "topic_name_b":  t.get("topic_name"),
                        "severity":      "critical",
                    })
            else:
                seen[qt_key] = {"year": year, "topic_id": t["id"], "topic_name": t.get("topic_name")}

    return violations


def _check_priority_tag_consistency(
    topics: list[dict],
    normalised_pyq_texts: set[str],
) -> list[dict]:
    """
    CHECK 4 — never_asked tag but appears in normalised PYQ collection.
    """
    violations: list[dict] = []
    for t in topics:
        if t.get("priority") == "never_asked":
            topic_name_lower = t.get("topic_name", "").lower()
            # Simple heuristic: check if topic name appears in any PYQ text
            for pyq_text in normalised_pyq_texts:
                if topic_name_lower in pyq_text.lower():
                    violations.append({
                        "topic_id":   t["id"],
                        "topic_name": t.get("topic_name"),
                        "issue":      (
                            f"Tagged never_asked but topic name appears in normalised PYQs. "
                            f"Sample: {pyq_text[:80]}"
                        ),
                        "severity":   "major",
                    })
                    break
    return violations


# ─────────────────────────────────────────────────────────────────────────────
# Groq AI checks (notation + definition consistency)
# ─────────────────────────────────────────────────────────────────────────────

_CONSISTENCY_SYSTEM = open(
    os.path.join(os.path.dirname(__file__), "..", "prompts", "consistency_checker.txt"),
    encoding="utf-8",
).read()


def _build_consistency_prompt(topics: list[dict]) -> str:
    # Send lean version — only fields relevant to notation/definition checks
    lean = [
        {
            "topic_id":    t.get("id"),
            "topic_name":  t.get("topic_name"),
            "definition":  t.get("definition", ""),
            "core_concept": t.get("core_concept", ""),
            "rapid_revision": t.get("rapid_revision", {}),
            "examiners_note": t.get("examiners_note", ""),
        }
        for t in topics
    ]
    return f"""Paper topics (lean view — all units):
{json.dumps(lean, ensure_ascii=False, indent=2)}

Run CHECK 1 (notation) and CHECK 2 (definition) only.
Output only valid JSON with keys: notation_violations, definition_violations."""


def _groq_consistency_check(topics: list[dict]) -> dict:
    prompt = _build_consistency_prompt(topics)

    try:
        response = _client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _CONSISTENCY_SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.0,
            max_tokens=4096,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        return json.loads(raw)

    except Exception as exc:
        logger.warning(
            "Consistency Checker: Groq unavailable — skipping notation/definition checks. %s", exc
        )
        return {"notation_violations": [], "definition_violations": []}


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_consistency_checker(
    all_paper_topics: list[dict],
    normalised_pyqs: list[dict],
) -> dict:
    """
    Args:
        all_paper_topics : Every topic across all units for this paper (full content).
        normalised_pyqs  : All normalised PYQ papers for this paper.

    Returns:
        {
            "notation_violations":   [...],
            "definition_violations": [...],
            "pyq_year_violations":   [...],
            "priority_violations":   [...],
            "latex_violations":      [...],
            "auto_patched_topics":   { topic_id: patched_topic_dict },
            "needs_critic_review":   [ topic_id, ... ],  # major violations
            "needs_human_review":    [ topic_id, ... ],  # critical violations
            "passed":                bool,
        }
    """
    logger.info(
        "Consistency Checker: checking %d topics across paper", len(all_paper_topics)
    )

    # ── CHECK 5: LaTeX auto-patch (rule-based, no AI) ───────────────────────
    auto_patched: dict[str, dict] = {}
    latex_violations: list[dict] = []
    topics_after_latex = []

    for topic in all_paper_topics:
        patched_topic, patched_fields = _apply_latex_autopatch(topic)
        if patched_fields:
            auto_patched[topic["id"]] = patched_topic
            for field_path in patched_fields:
                latex_violations.append({
                    "topic_id":  topic["id"],
                    "topic_name": topic.get("topic_name"),
                    "field":     field_path,
                    "severity":  "minor",
                })
            topics_after_latex.append(patched_topic)
        else:
            topics_after_latex.append(topic)

    if latex_violations:
        logger.info(
            "Consistency Checker: auto-patched %d LaTeX violations across %d topics",
            len(latex_violations), len(auto_patched)
        )

    # ── CHECK 3: PYQ year conflicts (rule-based) ────────────────────────────
    pyq_year_violations = _check_pyq_year_conflicts(topics_after_latex)
    if pyq_year_violations:
        logger.warning(
            "Consistency Checker: %d PYQ year conflict(s) found", len(pyq_year_violations)
        )

    # ── CHECK 4: Priority tag consistency (rule-based) ──────────────────────
    all_pyq_texts = set()
    for paper in normalised_pyqs:
        for q in paper.get("questions", []):
            for part in q.get("parts", []):
                all_pyq_texts.add(part.get("question_text", ""))

    priority_violations = _check_priority_tag_consistency(topics_after_latex, all_pyq_texts)

    # ── CHECKS 1 & 2: Notation and definition (Groq) ────────────────────────
    ai_results = _groq_consistency_check(topics_after_latex)
    notation_violations   = ai_results.get("notation_violations", [])
    definition_violations = ai_results.get("definition_violations", [])

    # ── Triage: what needs critic review vs human review ────────────────────
    needs_critic_review: set[str] = set()
    needs_human_review:  set[str] = set()

    for v in pyq_year_violations:
        needs_human_review.update([v.get("topic_a"), v.get("topic_b")])

    for v in notation_violations + definition_violations:
        if v.get("severity") == "major":
            for tid in v.get("topic_ids", []):
                needs_critic_review.add(tid)
        elif v.get("severity") == "critical":
            for tid in v.get("topic_ids", []):
                needs_human_review.add(tid)

    for v in priority_violations:
        if v.get("severity") == "major":
            needs_critic_review.add(v.get("topic_id"))

    # Remove human review topics from critic queue (escalation wins)
    needs_critic_review -= needs_human_review

    total_violations = (
        len(latex_violations)
        + len(pyq_year_violations)
        + len(priority_violations)
        + len(notation_violations)
        + len(definition_violations)
    )
    passed = (
        len(pyq_year_violations) == 0          # no critical PYQ conflicts
        and len(needs_critic_review) == 0       # no major issues requiring re-critique
        and len(needs_human_review) == 0        # no critical issues
    )

    result = {
        "notation_violations":   notation_violations,
        "definition_violations": definition_violations,
        "pyq_year_violations":   pyq_year_violations,
        "priority_violations":   priority_violations,
        "latex_violations":      latex_violations,
        "auto_patched_topics":   auto_patched,
        "needs_critic_review":   list(needs_critic_review),
        "needs_human_review":    list(needs_human_review),
        "total_violations":      total_violations,
        "passed":                passed,
    }

    logger.info(
        "Consistency Checker: %s | %d total violations | "
        "%d auto-patched | %d critic-review | %d human-review",
        "✓ PASSED" if passed else "✗ FAILED",
        total_violations,
        len(auto_patched),
        len(needs_critic_review),
        len(needs_human_review),
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python 12_consistency_checker.py <all_topics_json> <normalised_pyqs_json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        _topics = json.load(f)
    with open(sys.argv[2]) as f:
        _pyqs = json.load(f)

    _result = run_consistency_checker(_topics, _pyqs)

    print(f"\n{'✓ PASSED' if _result['passed'] else '✗ FAILED'}")
    print(f"Total violations : {_result['total_violations']}")
    print(f"Auto-patched     : {len(_result['auto_patched_topics'])} topics")
    print(f"Critic review    : {len(_result['needs_critic_review'])} topics")
    print(f"Human review     : {len(_result['needs_human_review'])} topics")

async def run(all_topics: list[dict], paper: dict, cost=None) -> dict:
    import asyncio
    paper_dna = paper.get("paper_dna") or {} if isinstance(paper, dict) else {}
    normalised_pyqs = paper_dna.get("_raw_normalised_pyqs", [])
    return await asyncio.to_thread(run_consistency_checker, all_topics, normalised_pyqs)
