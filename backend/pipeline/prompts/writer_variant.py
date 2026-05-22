"""
writer_variant.py
-----------------
Builds the user-turn message for each Writer (Agent 5) API call.

This is the VARIANT side of the Writer prompt — it changes per topic.
The INVARIANT side (writer_invariant.txt) is loaded once as the system prompt
and cached by the Anthropic API, saving 60–70% of Writer token cost.

Called by:  backend/pipeline/agents/05_writer.py
Returns:    str  — the complete user message to send with the Writer API call

All parameters come from the orchestrator, which assembles them from:
  - Supabase `topics` table  (topic_name, split_generation, etc.)
  - Supabase `papers` table  (upc, paper_type, diagram_heavy, primary_textbook, documentation_tier)
  - Agent 4 output           (concept_bridge, left_adjacent_topic, right_adjacent_topic)
  - Agent 3 output           (topic_dna, language_dna, combination_dna)
  - Agent 2 output           (topic_syllabus_content)
"""

from __future__ import annotations
import json


# ─── Note-style category derivation ────────────────────────────────────────────
# Derived from paper_type (from upc_registry.json). The Writer uses this to decide
# whether to generate numerical worked examples, theory examples, or diagram blocks.
#
# paper_type → note_style_category mapping:
#   "numerical"      → "numerical"
#   "theory"         → "theory"
#   "mixed"          → "mixed"       (Writer generates both types; depth calibrated per topic)
#   "life_sciences"  → "life_sciences"
#
# Passed in directly — do not derive here. Orchestrator sets it from papers.paper_type.

NOTE_STYLE_TO_EXAMPLE_TYPE: dict[str, str] = {
    "numerical":    "numerical",
    "theory":       "theory",
    "mixed":        "mixed",
    "life_sciences": "biological",
}


def build_writer_user_prompt(
    # ── Topic identity ──────────────────────────────────────────────────────────
    topic_name: str,
    topic_syllabus_content: list[str],     # Bullet points from syllabus for this topic only

    # ── Paper DNA signals ───────────────────────────────────────────────────────
    topic_dna: dict | None,                # From Agent 3 topic_dna array, this topic's entry
    language_dna: dict | None,             # From Agent 3 language_dna array, this topic's entry
    combination_dna: dict | None,          # From Agent 3 combination_dna array, this topic's entry

    # ── Agent 4 mapping signals ─────────────────────────────────────────────────
    concept_bridge: str | None,            # "Requires X. Why: Y. Bridge: Z." from Mapper
    left_adjacent_topic: str | None,       # Topic immediately before this in optimised sequence
    right_adjacent_topic: str | None,      # Topic immediately after this in optimised sequence

    # ── Paper-level context ─────────────────────────────────────────────────────
    note_style_category: str,              # "numerical" | "theory" | "mixed" | "life_sciences"
    diagram_heavy: bool,                   # From papers.diagram_heavy
    primary_textbook: str | None,          # From papers.primary_textbook (for diagram sourcing)
    documentation_tier: int,              # 1 | 2 | 3 | 4 — governs depth expectations

    # ── UPC identifier ──────────────────────────────────────────────────────────
    upc: str,

    # ── Split generation control ─────────────────────────────────────────────────
    split_generation: bool = False,
    split_mode: str | None = None,         # "content" | "examples" | None
) -> str:
    """
    Returns the complete user message string for a single Writer API call.

    Architecture note:
      The system prompt (writer_invariant.txt) is cached — it never changes.
      This function produces the user message only. Keep it clean and structured.
      The Writer reads this message and knows its rules from the cached system prompt.
    """

    # ── 1. Prerequisite bridge block ─────────────────────────────────────────────
    if concept_bridge:
        bridge_block = f"PREREQUISITE BRIDGE:\n{concept_bridge}"
    else:
        bridge_block = "PREREQUISITE: None"

    # ── 2. Adjacent topic boundary block ─────────────────────────────────────────
    adjacent_lines: list[str] = []
    if left_adjacent_topic:
        adjacent_lines.append(
            f"LEFT ADJACENT TOPIC (context only — do not teach this): {left_adjacent_topic}"
        )
    if right_adjacent_topic:
        adjacent_lines.append(
            f"RIGHT ADJACENT TOPIC (context only — do not teach this): {right_adjacent_topic}"
        )
    adjacent_block = "\n".join(adjacent_lines) if adjacent_lines else "ADJACENT TOPICS: None"

    # ── 3. Split generation instruction block ────────────────────────────────────
    if split_generation and split_mode == "content":
        split_block = (
            "━━ SPLIT GENERATION MODE — CONTENT CALL ━━\n"
            "Generate all fields EXCEPT examples and pyqs.\n"
            "Set examples: [] and pyqs: [] in your output.\n"
            "Do not attempt to generate examples or PYQ key_steps in this call.\n"
            "The Examples Call will fill those fields and they will be merged."
        )
    elif split_generation and split_mode == "examples":
        split_block = (
            "━━ SPLIT GENERATION MODE — EXAMPLES CALL ━━\n"
            "Generate ONLY the examples and pyqs fields.\n"
            "All other fields will be retained from the Content Call result.\n"
            "Do not regenerate any field except examples and pyqs.\n"
            "Treat the Content Call output as ground truth for all other fields."
        )
    else:
        split_block = ""

    # ── 4. DNA signal blocks ──────────────────────────────────────────────────────
    # Serialise to indented JSON for readability in the prompt.
    # If a DNA section is missing (e.g. Tier 3 paper with no PYQs), say so explicitly.

    if topic_dna:
        topic_dna_block = f"TOPIC DNA:\n{json.dumps(topic_dna, indent=2)}"
    else:
        topic_dna_block = (
            "TOPIC DNA: Not available.\n"
            "No NEP PYQ data for this topic. Use syllabus hours for depth calibration.\n"
            "Set priority based on syllabus position and hours weighting."
        )

    if language_dna:
        language_dna_block = f"LANGUAGE DNA:\n{json.dumps(language_dna, indent=2)}"
    else:
        language_dna_block = (
            "LANGUAGE DNA: Not available.\n"
            "Set rapid_revision.examiner_pattern to:\n"
            "\"No NEP exam data available for this topic.\""
        )

    if combination_dna:
        combination_dna_block = f"COMBINATION DNA:\n{json.dumps(combination_dna, indent=2)}"
    else:
        combination_dna_block = (
            "COMBINATION DNA: Not available.\n"
            "Do not reference any combination patterns in Examiner's Note."
        )

    # ── 5. Documentation tier instruction ────────────────────────────────────────
    tier_instructions = {
        1: (
            "DOCUMENTATION TIER: 1 — Fully Calibrated.\n"
            "3+ NEP PYQ years available. Full DNA signals available.\n"
            "Every Examiner's Note must reference a specific PYQ year.\n"
            "Use all DNA signals. Full depth expected for all high-priority topics."
        ),
        2: (
            "DOCUMENTATION TIER: 2 — Partially Calibrated.\n"
            "1–2 NEP PYQ years available. Partial DNA signals available.\n"
            "Use available DNA signals fully.\n"
            "Examiner's Note should reference available PYQ year(s) where possible."
        ),
        3: (
            "DOCUMENTATION TIER: 3 — Syllabus-Based.\n"
            "No NEP PYQs publicly available. DNA signals unavailable.\n"
            "Set depth_signal_source to \"syllabus_hours\" for all topics.\n"
            "Set rapid_revision.examiner_pattern to \"No NEP exam data available for this topic.\"\n"
            "Do not invent PYQ patterns. Do not reference years. Generate from syllabus only."
        ),
        4: (
            "DOCUMENTATION TIER: 4 — Insufficient Data.\n"
            "Pipeline should not have reached Agent 5 for a Tier 4 paper.\n"
            "If you receive this: return all fields as null and set priority to \"never_asked\"."
        ),
    }
    tier_block = tier_instructions.get(
        documentation_tier,
        f"DOCUMENTATION TIER: {documentation_tier} — Unknown tier. Treat as Tier 3."
    )

    # ── 6. Paper context block ────────────────────────────────────────────────────
    example_type = NOTE_STYLE_TO_EXAMPLE_TYPE.get(note_style_category, "theory")
    textbook_line = f"PRIMARY TEXTBOOK: {primary_textbook}" if primary_textbook else (
        "PRIMARY TEXTBOOK: Not specified. Use standard DU syllabus textbook conventions."
    )

    paper_context_block = "\n".join([
        f"UPC: {upc}",
        f"NOTE STYLE CATEGORY: {note_style_category}",
        f"EXAMPLE TYPE TO GENERATE: {example_type}",
        f"DIAGRAM HEAVY: {diagram_heavy}",
        textbook_line,
        tier_block,
    ])

    # ── 7. Syllabus content block ─────────────────────────────────────────────────
    if topic_syllabus_content:
        syllabus_lines = "\n".join(f"  - {item}" for item in topic_syllabus_content)
        syllabus_block = f"SYLLABUS CONTENT FOR THIS TOPIC:\n{syllabus_lines}"
    else:
        syllabus_block = (
            "SYLLABUS CONTENT FOR THIS TOPIC: Not specified in syllabus beyond topic name.\n"
            "Generate from the topic name and available DNA signals only.\n"
            "Do not invent content beyond what the topic name implies."
        )

    # ── 8. Assemble the final prompt ──────────────────────────────────────────────
    # Section separator for Writer readability. Clean, structured, unambiguous.
    SEP = "━" * 60

    sections: list[str] = [
        f"TOPIC: {topic_name}",
        SEP,
        paper_context_block,
        SEP,
        syllabus_block,
        SEP,
        bridge_block,
        adjacent_block,
        SEP,
        topic_dna_block,
        SEP,
        language_dna_block,
        SEP,
        combination_dna_block,
    ]

    # Only include split block if in split mode
    if split_block:
        sections.extend([SEP, split_block])

    sections.append(SEP)
    sections.append(
        "Generate the topic JSON now.\n"
        "Output only valid JSON matching topic_output_schema.json.\n"
        "No prose. No markdown fences. No preamble. Start your output with { and end with }."
    )

    return "\n\n".join(sections)


# ─── Convenience: build for a simple non-split call ─────────────────────────────
def build_writer_prompt_simple(
    topic_name: str,
    topic_syllabus_content: list[str],
    topic_dna: dict | None,
    language_dna: dict | None,
    combination_dna: dict | None,
    concept_bridge: str | None,
    left_adjacent_topic: str | None,
    right_adjacent_topic: str | None,
    note_style_category: str,
    diagram_heavy: bool,
    primary_textbook: str | None,
    documentation_tier: int,
    upc: str,
) -> str:
    """Convenience wrapper for the common non-split case."""
    return build_writer_user_prompt(
        topic_name=topic_name,
        topic_syllabus_content=topic_syllabus_content,
        topic_dna=topic_dna,
        language_dna=language_dna,
        combination_dna=combination_dna,
        concept_bridge=concept_bridge,
        left_adjacent_topic=left_adjacent_topic,
        right_adjacent_topic=right_adjacent_topic,
        note_style_category=note_style_category,
        diagram_heavy=diagram_heavy,
        primary_textbook=primary_textbook,
        documentation_tier=documentation_tier,
        upc=upc,
        split_generation=False,
        split_mode=None,
    )