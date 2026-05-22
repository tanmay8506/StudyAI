"""
update_claude_refs.py
Replaces all Claude/Anthropic references with Gemini 2.0 Flash across PLAN files.
Run from the PLAN directory.
"""
import os

FILES = [
    "StudyAI_Plan.txt",
    "StudyAI_Build_Guide.txt",
    "Plan.md.txt",
    "StudyAI_Technical_Reference.txt",
]

REPLACEMENTS = [
    # Model name variants
    ("claude-sonnet-4-6",          "gemini-2.0-flash"),
    ("Claude Sonnet 4.6",          "Gemini 2.0 Flash"),
    ("Claude Sonnet 4-6",          "Gemini 2.0 Flash"),
    ("Claude Sonnet",              "Gemini 2.0 Flash"),
    ("claude sonnet",              "Gemini 2.0 Flash"),
    ("Claude Haiku",               "Gemini 2.0 Flash"),

    # Parenthetical model labels
    ("(Claude, combined with Topic DNA call)", "(Gemini 2.0 Flash, combined with Topic DNA call)"),
    ("(Claude, separate call)",    "(Gemini 2.0 Flash, separate call)"),
    ("(Claude)",                   "(Gemini 2.0 Flash)"),

    # Proof verifier
    ("Claude proof verifier",      "Gemini proof verifier"),
    ("A Claude call",              "A Gemini call"),
    ("One additional Claude call", "One additional Gemini call"),

    # Provider / SDK / API key references
    ("Anthropic (Claude)",         "Google (Gemini 2.0 Flash)"),
    ("Anthropic API key",          "Google AI (Gemini) API key"),
    ("Anthropic SDK",              "google-generativeai SDK"),
    ("anthropic",                  "google-generativeai"),
    ("| **Anthropic** |",          "| **Google** |"),

    # Paid/free tier descriptions
    ("PAID — Claude Sonnet (Writer + Critic only)",
     "FREE — Gemini 2.0 Flash (Writer + Critic + Mapper + Paper DNA)"),
    ("Tier 1 — Quality-Critical (Claude Sonnet 4.6) — PAID, used sparingly:",
     "Tier 1 — Quality-Critical (Gemini 2.0 Flash) — FREE via Google AI Studio:"),
    ("— PAID, used sparingly",     "— FREE via Google AI Studio"),

    # Strategy / model selection descriptions
    ("use Sonnet ONLY where quality directly affects the final product (Writer + Critic). "
     "Everything else uses free-tier models.",
     "use Gemini 2.0 Flash for ALL quality-critical roles (Writer, Critic, Mapper, Paper DNA) "
     "— all FREE via Google AI Studio."),
    ("Claude Sonnet is used for exactly 2 agent types (~24-32 calls). Everything else is free or near-free.",
     "Gemini 2.0 Flash is used for all quality-critical agents — entirely FREE via Google AI Studio."),
    ("Claude Sonnet ONLY for Writer + Critic. Gemini Pro (free) for reasoning tasks. "
     "Gemini Flash (free) for execution tasks.",
     "Gemini 2.0 Flash for ALL quality-critical roles (Writer, Critic, Mapper, Paper DNA) — all FREE."),

    # Budget/cost lines
    ("Budget for first paper (including 5-10 prompt tuning iterations): ~$8-15. "
     "Use DeepSeek V3 for early prompt iterations, switch to Claude Sonnet for final quality runs.",
     "Budget for first paper: $0. Gemini 2.0 Flash is fully free via Google AI Studio."),
    ("Claude API costs",           "API costs"),
    ("Switch back to Claude Sonnet for final runs.", "Gemini 2.0 Flash is free and production-ready."),
    ("Switch back to Claude Sonnet for final quality runs.", "Gemini 2.0 Flash is already free and production-quality."),

    # DeepSeek backup note
    ("DeepSeek as Claude backup",  "DeepSeek as fallback"),
    ("temporarily replace Claude Sonnet for Writer testing iterations",
     "temporarily replace Gemini 2.0 Flash for Writer testing iterations"),
    ("OPTIONAL — DeepSeek V3 (cheap Claude alternative for prompt tuning iterations)",
     "OPTIONAL — DeepSeek V3 (alternative for prompt tuning iterations)"),

    # Column headers / table rows
    ("Why Claude specifically",    "Why Gemini 2.0 Flash"),
    ("None — paid only",           "Free tier (AI Studio)"),
    ("Claude Sonnet (paid)",       "Gemini 2.0 Flash (free)"),

    # Example output labels
    ("Topic DNA — Example Output (Claude)",       "Topic DNA — Example Output (Gemini 2.0 Flash)"),
    ("Language DNA — Example Output (Claude)",    "Language DNA — Example Output (Gemini 2.0 Flash)"),
    ("Combination DNA — Example Output (Claude)", "Combination DNA — Example Output (Gemini 2.0 Flash)"),

    # Misc
    ("Claude generates SVG code",  "AI-generated SVG code"),
    ("PAID — Claude",              "FREE — Gemini 2.0 Flash"),

    # Agent descriptions in pipeline diagrams
    ("Agent 5. Claude Sonnet. One call per topic.",
     "Agent 5. Gemini 2.0 Flash. One call per topic."),
    ("Agent 8. Claude Sonnet. Field-level critique per topic.",
     "Agent 8. Gemini 2.0 Flash. Field-level critique per topic."),

    # Paper DNA references
    ("Call 1 produces Topic DNA and Language DNA together (Claude).",
     "Call 1 produces Topic DNA and Language DNA together (Gemini 2.0 Flash)."),
    ("Call 2 produces Combination DNA (Claude).",
     "Call 2 produces Combination DNA (Gemini 2.0 Flash)."),
]


def update_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        changed = sum(1 for o, n in REPLACEMENTS if o in original)
        print(f"  [OK] Updated: {os.path.basename(filepath)}  ({changed} replacement types applied)")
    else:
        print(f"  — No changes needed: {os.path.basename(filepath)}")


if __name__ == "__main__":
    plan_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Running in: {plan_dir}\n")
    for fname in FILES:
        fpath = os.path.join(plan_dir, fname)
        if os.path.exists(fpath):
            update_file(fpath)
        else:
            print(f"  NOT FOUND: {fname}")
    print("\nDone.")
