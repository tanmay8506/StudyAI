"""
utils/depth_signal.py
──────────────────────
Resolves the depth signal source for a topic.

The depth_signal_source field tells the Writer how much depth
(length, detail, and example count) to apply to a topic.

Sources:
  "syllabus_hours"   — derived from unit hours / topic count
  "pyq_appearances"  — topic appeared many times in PYQs (high depth)
  "examiner_pattern" — topic has specific examiner language patterns
  "default"          — no signal available
"""

from __future__ import annotations


def resolve_depth_signal(
    topic_name: str,
    unit_hours: float | None,
    unit_topic_count: int,
    pyq_appearances: int = 0,
) -> str:
    """
    Return the depth_signal_source string for a topic.

    Args:
        topic_name:        The topic name (used for pattern matching).
        unit_hours:        Total hours allocated to the parent unit.
        unit_topic_count:  Number of topics in the parent unit.
        pyq_appearances:   Number of times this topic appeared in PYQs.

    Returns:
        One of: "syllabus_hours", "pyq_appearances", "default".
    """
    if pyq_appearances >= 3:
        return "pyq_appearances"

    if unit_hours is not None and unit_topic_count > 0:
        hours_per_topic = unit_hours / unit_topic_count
        if hours_per_topic >= 2.5:
            return "syllabus_hours"

    return "default"
