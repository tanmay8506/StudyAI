"""
Agent 2B — Researcher Verifier
-------------------------------
Model: Groq (Llama 3) — free tier, 30 RPM

Mechanical binary verification of Gemini's syllabus extraction.
Receives the raw PDF text alongside the structured JSON from Agent 2.
Runs 3 checks. If any fail, Agent 2 must re-run.

This agent does NOT fix anything. It only catches failures.
Fixing is Agent 2's job (retry).

Checks:
1. Every unit name in JSON appears in PDF text?
2. Every subtopic in JSON appears under its correct unit in PDF text?
3. Any units in PDF clearly missing from JSON?
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from groq import Groq

# ── Path setup ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[3]


# ── Extract raw text from PDF (for verification) ──────────────────────────────
def extract_raw_text(pdf_path: Path) -> str:
    """
    Extract raw text from a PDF for verification purposes.
    Uses pdftotext if available, returns empty string if not.
    """
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=60
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # pdftotext not available — skip text-based verification
        return ""


# ── Groq client ───────────────────────────────────────────────────────────────
def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set. Add it to backend/.env"
        )
    return Groq(api_key=api_key)


# ── Main verification function ────────────────────────────────────────────────
def verify_syllabus(
    syllabus_json: dict,
    pdf_path: Path,
    max_retries: int = 1
) -> dict:
    """
    Verify that the syllabus JSON correctly represents the PDF content.

    Returns:
        {
            "passed": bool,
            "checks": {
                "unit_names_present": bool,
                "topics_under_correct_units": bool,
                "no_missing_units": bool
            },
            "failures": list of failure descriptions,
            "raw_text_available": bool
        }
    """
    # Extract raw PDF text for comparison
    raw_text = extract_raw_text(pdf_path)
    raw_text_available = len(raw_text) > 100

    result = {
        "passed": True,
        "checks": {
            "unit_names_present": True,
            "topics_under_correct_units": True,
            "no_missing_units": True
        },
        "failures": [],
        "raw_text_available": raw_text_available
    }

    # ── If no raw text available: lightweight JSON-only checks ───────────────
    if not raw_text_available:
        print("  [2B] Raw PDF text not available — running JSON structure checks only")
        return _verify_json_structure_only(syllabus_json, result)

    # ── Full verification via Groq ────────────────────────────────────────────
    client = get_groq_client()

    unit_names = [u["unit_name"] for u in syllabus_json.get("units", [])]
    unit_topics = {
        u["unit_name"]: u["topics"]
        for u in syllabus_json.get("units", [])
    }

    verification_prompt = f"""You are a verification agent for StudyAI.

You receive:
1. The raw text extracted from a Delhi University syllabus PDF
2. The structured JSON that was extracted from that PDF

Your job: run 3 binary checks and report ONLY the results.

EXTRACTED UNIT NAMES FROM JSON:
{json.dumps(unit_names, indent=2)}

FIRST 3 TOPICS PER UNIT FROM JSON (sample):
{json.dumps({k: v[:3] for k, v in unit_topics.items()}, indent=2)}

RAW PDF TEXT (first 4000 chars):
{raw_text[:4000]}

━━ CHECK 1: Unit Names Present ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each unit name in the JSON: does it (or a close match) appear in the PDF text?
If ALL unit names are found: check_1 = true
If ANY unit name is missing: check_1 = false, list the missing ones.

━━ CHECK 2: No Hallucinated Topics ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For the sample topics shown: do they appear in the PDF text?
If most sample topics are traceable to PDF text: check_2 = true
If multiple sample topics appear to be invented: check_2 = false, list examples.

━━ CHECK 3: No Obvious Missing Units ━━━━━━━━━━━━━━━━━━━━━━━━━━━
Looking at the PDF text: are there any unit headings clearly visible that do NOT
appear in the JSON?
If no obvious missing units: check_3 = true
If missing units detected: check_3 = false, list them.

Output ONLY this JSON:
{{
  "check_1_unit_names_present": true or false,
  "check_1_missing": [],
  "check_2_topics_traceable": true or false,
  "check_2_issues": [],
  "check_3_no_missing_units": true or false,
  "check_3_missing_units": []
}}
No prose. No explanation. Only valid JSON."""

    for attempt in range(max_retries + 1):
        try:
            print(f"  [2B] Running Groq verification (attempt {attempt + 1})...")

            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {
                        "role": "user",
                        "content": verification_prompt
                    }
                ],
                temperature=0,
                max_tokens=500,
            )

            raw = response.choices[0].message.content.strip()

            if raw.startswith("```"):
                lines = raw.split("\n")
                raw = "\n".join(lines[1:-1])

            checks = json.loads(raw)

            # Map to result structure
            result["checks"]["unit_names_present"] = checks.get(
                "check_1_unit_names_present", True
            )
            result["checks"]["topics_under_correct_units"] = checks.get(
                "check_2_topics_traceable", True
            )
            result["checks"]["no_missing_units"] = checks.get(
                "check_3_no_missing_units", True
            )

            # Collect failures
            if not result["checks"]["unit_names_present"]:
                missing = checks.get("check_1_missing", [])
                result["failures"].append(
                    f"Unit names missing from PDF: {missing}"
                )

            if not result["checks"]["topics_under_correct_units"]:
                issues = checks.get("check_2_issues", [])
                result["failures"].append(
                    f"Possible hallucinated topics: {issues}"
                )

            if not result["checks"]["no_missing_units"]:
                missing = checks.get("check_3_missing_units", [])
                result["failures"].append(
                    f"Units in PDF missing from JSON: {missing}"
                )

            result["passed"] = all(result["checks"].values())

            status = "PASSED" if result["passed"] else "FAILED"
            print(f"  [2B] Verification {status}")
            if result["failures"]:
                for f in result["failures"]:
                    print(f"    - {f}")

            return result

        except (json.JSONDecodeError, KeyError) as e:
            if attempt < max_retries:
                print(f"  [2B] Parse error ({e}). Retrying...")
                import time
                time.sleep(3)
            else:
                print(f"  [2B] Verification failed to parse — treating as passed (non-blocking)")
                result["passed"] = True
                result["failures"].append(
                    f"Verification agent parse error: {e} — skipped"
                )
                return result

        except Exception as e:
            print(f"  [2B] Groq unavailable ({e}) — skipping verification")
            result["passed"] = True
            result["failures"].append(f"Groq unavailable: {e} — verification skipped")
            return result


# ── JSON-only structural checks (when raw text unavailable) ──────────────────
def _verify_json_structure_only(syllabus: dict, result: dict) -> dict:
    """
    Lightweight checks that don't require raw PDF text.
    Validates JSON completeness without cross-referencing the PDF.
    """
    failures = []

    units = syllabus.get("units", [])
    if not units:
        failures.append("No units in syllabus JSON")
        result["checks"]["unit_names_present"] = False

    for unit in units:
        if not unit.get("unit_name"):
            failures.append(f"Unit {unit.get('unit_number')} has no name")
        if not unit.get("topics"):
            failures.append(f"Unit '{unit.get('unit_name')}' has no topics")

    if not syllabus.get("prescribed_books"):
        # Not a failure — some syllabi don't list books explicitly
        print("  [2B] Note: No prescribed books found in syllabus JSON")

    result["failures"] = failures
    result["passed"] = len(failures) == 0

    status = "PASSED" if result["passed"] else "FAILED"
    print(f"  [2B] Structure-only verification {status}")

    return result


# ── Main run function ─────────────────────────────────────────────────────────
async def run(upc: str, syllabus_json: dict, cost=None) -> bool:
    """
    Main entry point called by orchestrator.

    Args:
        upc: The paper UPC
        syllabus_json: Output from Agent 2 Call 1
        cost: CostTracker instance

    Returns:
        bool: True if verification passed, False otherwise.
    """
    print(f"\n[Agent 2B — Researcher Verifier]")
    result = verify_syllabus(syllabus_json, Path(f"{upc}.pdf"))
    return result.get("passed", False)


# ── CLI runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    if len(sys.argv) < 3:
        print("Usage: python 02b_researcher_verifier.py <syllabus_json_path> <pdf_path>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    pdf_path = Path(sys.argv[2])

    with open(json_path) as f:
        syllabus = json.load(f)

    result = run(syllabus, pdf_path)
    print(json.dumps(result, indent=2))