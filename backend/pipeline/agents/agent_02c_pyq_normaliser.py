"""
Agent 2C — PYQ Normaliser
--------------------------
Model: Groq (Llama 3) — free tier, 30 RPM

Receives raw PYQ data from Agent 2 and normalises it into
the strict pyq_normalised_schema.json format.

DU question papers are NOT standardised across colleges or years.
Some use Roman numerals for questions, some use brackets for marks,
some have combined questions with shared stem text.
This agent handles all of that and outputs one consistent format
that all downstream agents (Paper DNA, Examiner, Patcher) can rely on.

One Groq call per PYQ paper.
"""

import json
import os
import sys
import time
from pathlib import Path

from groq import Groq

# ── Path setup ───────────────────────────────────────────────────────────────
SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "schemas"
PYQ_SCHEMA_PATH = SCHEMAS_DIR / "pyq_normalised_schema.json"


# ── Load schema ───────────────────────────────────────────────────────────────
def load_pyq_schema() -> dict:
    if not PYQ_SCHEMA_PATH.exists():
        raise FileNotFoundError(f"PYQ schema not found at {PYQ_SCHEMA_PATH}")
    with open(PYQ_SCHEMA_PATH) as f:
        return json.load(f)


# ── Groq client ───────────────────────────────────────────────────────────────
def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set in backend/.env")
    return Groq(api_key=api_key)


# ── Build normalisation prompt ────────────────────────────────────────────────
def build_normalisation_prompt(raw_pyq: dict, schema: dict) -> str:
    return f"""You are the PYQ Normaliser for StudyAI.

You receive raw question paper data extracted by an AI from a Delhi University PDF.
Your job: normalise it into a strict, consistent JSON format.

━━ WHAT YOU MUST DO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. QUESTION NUMBERS
   Standardise to integers: Q.1 → 1, Q.I → 1, Question 1 → 1
   
2. MARKS
   Extract marks from wherever they appear: [6], (6 marks), 6 Marks
   If marks are missing for a part: distribute from total proportionally
   Add note in normalisation_notes if you had to distribute.

3. SUB-PARTS  
   Split into individual part objects: (a), (b), (c) → separate parts
   If no sub-parts: single part object with part: null

4. INSTRUCTION WORDS
   Extract VERBATIM — do not standardise.
   "State and prove" stays "State and prove" — not just "prove"
   "Find" stays "Find" — not "Calculate"
   If no instruction word visible: use "answer"

5. CHOICES (OR questions)
   If a question says "OR" between alternatives:
   Set has_choice: true on the first option
   Put the alternative in choice_alternative

6. QUESTION TEXT
   Keep verbatim. Do not clean up or paraphrase.
   Remove only obvious OCR artifacts (e.g. random symbols).

7. YEAR
   year_confirmed: true ONLY if year appears in document text (not just filename).
   year_confidence: "confirmed" or "unconfirmed"

━━ OUTPUT FORMAT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output ONLY valid JSON matching this schema structure:
{json.dumps(schema, indent=2)}

━━ RAW INPUT DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{json.dumps(raw_pyq, indent=2)}

Output ONLY valid JSON. No prose. No markdown fences. Just the JSON object."""


# ── Normalise a single PYQ paper ──────────────────────────────────────────────
def normalise_single_pyq(
    raw_pyq: dict,
    schema: dict,
    client: Groq,
    max_retries: int = 2
) -> dict:
    """
    Normalise one raw PYQ dict into the standard schema.
    Returns normalised dict.
    """
    year = raw_pyq.get("year", "unknown")
    prompt = build_normalisation_prompt(raw_pyq, schema)

    for attempt in range(max_retries + 1):
        try:
            print(f"  [2C] Normalising PYQ {year} (attempt {attempt + 1})...")

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=4096,
            )

            raw_text = response.choices[0].message.content.strip()

            if raw_text.startswith("```"):
                lines = raw_text.split("\n")
                raw_text = "\n".join(lines[1:-1])

            normalised = json.loads(raw_text)

            # Validate minimum structure
            if "questions" not in normalised:
                raise ValueError("Normalised output has no 'questions' field")

            if not normalised["questions"]:
                raise ValueError("Normalised output has empty questions list")

            # Ensure year fields are set
            if "year" not in normalised or normalised["year"] is None:
                normalised["year"] = raw_pyq.get("year")
                normalised["year_confirmed"] = raw_pyq.get("year_confirmed", False)
                normalised["year_confidence"] = "unconfirmed"

            normalised.setdefault("source_file", raw_pyq.get("source_file", "unknown"))
            normalised.setdefault("source_url", raw_pyq.get("source_url", None))
            normalised.setdefault("normalisation_notes", [])

            # Count total marks for validation
            total_parts = sum(
                len(q.get("parts", [])) for q in normalised["questions"]
            )

            print(f"  [2C] PYQ {year} normalised: "
                  f"{len(normalised['questions'])} questions, "
                  f"{total_parts} total parts")

            return normalised

        except (json.JSONDecodeError, ValueError) as e:
            if attempt < max_retries:
                print(f"  [2C] Normalisation parse error ({e}). Retrying in 3s...")
                time.sleep(3)
            else:
                # Return best-effort: wrap raw data in minimal valid structure
                print(f"  [2C] Normalisation failed after {max_retries+1} attempts. "
                      f"Using fallback structure.")
                return _fallback_normalise(raw_pyq, str(e))

        except Exception as e:
            if attempt < max_retries:
                print(f"  [2C] Groq error ({e}). Retrying in 5s...")
                time.sleep(5)
            else:
                print(f"  [2C] Groq unavailable. Using fallback structure.")
                return _fallback_normalise(raw_pyq, str(e))


# ── Fallback normalisation (when Groq fails) ──────────────────────────────────
def _fallback_normalise(raw_pyq: dict, error: str) -> dict:
    """
    Emergency fallback: convert raw_pyq to minimal valid structure.
    Used when Groq fails. Marks the paper with a warning note.
    Output will be lower quality but pipeline continues.
    """
    questions = []

    raw_questions = raw_pyq.get("questions", [])
    for i, q in enumerate(raw_questions):
        # Handle both pre-structured and flat raw formats
        if isinstance(q, dict) and "parts" in q:
            questions.append(q)
        elif isinstance(q, dict):
            questions.append({
                "number": q.get("number", i + 1),
                "total_marks": q.get("marks", q.get("total_marks", 0)),
                "compulsory": q.get("compulsory", False),
                "section": q.get("section", None),
                "parts": [{
                    "part": None,
                    "marks": q.get("marks", q.get("total_marks", 0)),
                    "instruction_word": q.get("instruction_word", "answer"),
                    "topic_hint": q.get("topic_hint", ""),
                    "question_text": q.get("question_text", str(q)),
                    "has_choice": False,
                    "choice_alternative": None,
                }]
            })

    return {
        "year": raw_pyq.get("year"),
        "year_confirmed": raw_pyq.get("year_confirmed", False),
        "year_confidence": "unconfirmed",
        "source_file": raw_pyq.get("source_file", "unknown"),
        "source_url": raw_pyq.get("source_url", None),
        "total_marks": raw_pyq.get("total_marks"),
        "duration_minutes": None,
        "questions": questions,
        "normalisation_notes": [
            f"FALLBACK: Groq normalisation failed ({error}). "
            "Manual review recommended for this PYQ year."
        ]
    }


# ── Main run function ─────────────────────────────────────────────────────────
def run_sync(raw_pyqs: list[dict]) -> list[dict]:
    """
    Main entry point called by orchestrator.

    Args:
        raw_pyqs: List of raw PYQ dicts from Agent 2

    Returns:
        List of normalised PYQ dicts in standard schema format.
        One dict per PYQ year. This is what all downstream agents use.
    """
    if not raw_pyqs:
        print("[Agent 2C — PYQ Normaliser] No PYQs to normalise.")
        return []

    print(f"\n[Agent 2C — PYQ Normaliser] Normalising {len(raw_pyqs)} PYQ paper(s)...")

    schema = load_pyq_schema()
    client = get_groq_client()

    normalised_pyqs = []

    for i, raw_pyq in enumerate(raw_pyqs):
        year = raw_pyq.get("year", "unknown")
        normalised = normalise_single_pyq(raw_pyq, schema, client)
        normalised_pyqs.append(normalised)

        # Rate limit buffer between Groq calls
        if i < len(raw_pyqs) - 1:
            time.sleep(2)

    print(f"[Agent 2C — PYQ Normaliser] Complete: {len(normalised_pyqs)} papers normalised")

    # Log any papers with fallback notes
    for pyq in normalised_pyqs:
        if pyq.get("normalisation_notes"):
            for note in pyq["normalisation_notes"]:
                if "FALLBACK" in note:
                    print(f"  WARNING: PYQ {pyq['year']} used fallback normalisation")

    return normalised_pyqs


# ── CLI runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    if len(sys.argv) < 2:
        print("Usage: python 02c_pyq_normaliser.py <raw_pyq_json_path>")
        print("The JSON file should contain a list of raw PYQ dicts.")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    with open(input_path) as f:
        raw = json.load(f)

    # Accept both single dict and list
    if isinstance(raw, dict):
        raw = [raw]

    result = run_sync(raw)
    print("\n=== NORMALISED OUTPUT ===")
    print(json.dumps(result, indent=2))

async def run(raw_pyq: dict, upc: str, cost=None) -> dict:
    import asyncio
    schema = load_pyq_schema()
    client = get_groq_client()
    return await asyncio.to_thread(normalise_single_pyq, raw_pyq, schema, client)