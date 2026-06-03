"""
utils/tier_classifier.py
─────────────────────────
Classifies a paper/topic into a documentation tier.

Tiers control Writer depth and detail level:
  Tier 1 — Minimal: brief definition + key formula only
  Tier 2 — Standard: full content including analogy + examples (default)
  Tier 3 — Comprehensive: split generation with extra examples + PYQ coverage
"""

from __future__ import annotations


def classify_tier(
    unit_hours: float | None,
    topic_count: int,
    pyq_appearances: int = 0,
    paper_type: str = "theory",
) -> int:
    """
    Return the documentation tier (1, 2, or 3) for a topic.

    Args:
        unit_hours:       Hours allocated to the parent unit in the syllabus.
        topic_count:      Number of topics in the unit.
        pyq_appearances:  How many times this topic appeared in PYQs.
        paper_type:       "theory", "applied", or "numerical".

    Returns:
        1 (minimal), 2 (standard), or 3 (comprehensive).
    """
    # Heavy PYQ appearances → comprehensive
    if pyq_appearances >= 4:
        return 3

    # High hours per topic AND theory paper → comprehensive
    if unit_hours and topic_count > 0:
        hours_per_topic = unit_hours / topic_count
        if hours_per_topic >= 3.0 and paper_type == "theory":
            return 3
        if hours_per_topic >= 2.0:
            return 2

    # Numerical papers → standard at minimum (need worked examples)
    if paper_type == "numerical":
        return 2

    # Low hours per topic → minimal
    if unit_hours and topic_count > 0:
        if unit_hours / topic_count < 1.0:
            return 1

    return 2  # Default: standard
