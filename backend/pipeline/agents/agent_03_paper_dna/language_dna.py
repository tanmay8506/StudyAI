"""
03_paper_dna/language_dna.py
─────────────────────────────
Agent 3 — Language DNA standalone module.

Provides language_dna utilities used by topic_dna.py and directly
by the Mental Model Mapper (Agent 4) when it needs to annotate
concept_bridge sentences with the exact instruction words DU uses.

Also exposes get_dominant_instruction_word() — used by the Writer
to set examiner_pattern in rapid_revision.
"""

from __future__ import annotations

from typing import Any, Optional


def get_dominant_instruction_word(language_dna_for_topic: dict[str, Any]) -> Optional[str]:
    """
    Return the single most-used instruction word for a topic.

    Args:
        language_dna_for_topic: One language_dna object for a specific topic.

    Returns:
        The most common instruction word (e.g. "find", "prove") or None if empty.
    """
    instruction_words: dict[str, int] = language_dna_for_topic.get("instruction_words", {})
    if not instruction_words:
        return None
    return max(instruction_words, key=lambda k: instruction_words[k])


def get_language_dna_for_topic(
    language_dna: list[dict[str, Any]],
    topic_name: str,
) -> Optional[dict[str, Any]]:
    """
    Retrieve language DNA for a specific topic by exact name match, then
    case-insensitive fallback.

    Args:
        language_dna: Full language_dna list from paper_dna_schema.json.
        topic_name:   Name of the topic to look up.

    Returns:
        The language_dna object for the topic, or None if not found.
    """
    # Exact match first
    for item in language_dna:
        if item.get("topic_name") == topic_name:
            return item

    # Case-insensitive fallback
    topic_lower = topic_name.lower()
    for item in language_dna:
        if item.get("topic_name", "").lower() == topic_lower:
            return item

    return None


def get_topic_dna_for_topic(
    topic_dna: list[dict[str, Any]],
    topic_name: str,
) -> Optional[dict[str, Any]]:
    """
    Retrieve topic DNA for a specific topic by exact name, then case-insensitive.
    """
    for item in topic_dna:
        if item.get("topic_name") == topic_name:
            return item
    topic_lower = topic_name.lower()
    for item in topic_dna:
        if item.get("topic_name", "").lower() == topic_lower:
            return item
    return None


def get_combination_dna_for_topic(
    combination_dna: list[dict[str, Any]],
    topic_name: str,
) -> Optional[dict[str, Any]]:
    """
    Retrieve combination DNA for a specific topic by exact name, then case-insensitive.
    """
    for item in combination_dna:
        if item.get("topic_name") == topic_name:
            return item
    topic_lower = topic_name.lower()
    for item in combination_dna:
        if item.get("topic_name", "").lower() == topic_lower:
            return item
    return None


def build_examiner_pattern_string(
    language_dna_item: Optional[dict[str, Any]],
    topic_dna_item: Optional[dict[str, Any]],
    combination_dna_item: Optional[dict[str, Any]],
) -> str:
    """
    Build the examiner_pattern string for rapid_revision.
    This is what the Writer injects into rapid_revision.examiner_pattern.

    Format: "DU uses '[instruction_word]' for this topic.
             Typical phrasing: '[typical_phrasing]'.
             [Combination pattern if applicable.]"

    Args:
        language_dna_item:    Language DNA for this topic (may be None).
        topic_dna_item:       Topic DNA for this topic (may be None).
        combination_dna_item: Combination DNA for this topic (may be None).

    Returns:
        A single string for the examiner_pattern field.
    """
    if not language_dna_item:
        return "No NEP exam data available for this topic."

    dominant_word = get_dominant_instruction_word(language_dna_item)
    typical_phrasing = language_dna_item.get("typical_phrasing", "")

    parts = []

    if dominant_word:
        parts.append(f"DU uses '{dominant_word}' for this topic.")

    if typical_phrasing:
        parts.append(f"Typical phrasing: \"{typical_phrasing}\".")

    # Add combination pattern if topic is always combined
    if combination_dna_item:
        always_with = combination_dna_item.get("always_asked_with", [])
        combo_pattern = combination_dna_item.get("combination_pattern", "")
        if always_with and combo_pattern and combo_pattern != "No consistent combination pattern detected.":
            parts.append(
                f"Often asked together with {', '.join(always_with)}: \"{combo_pattern}\"."
            )

    if not parts:
        return "No NEP exam data available for this topic."

    return " ".join(parts)