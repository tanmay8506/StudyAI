"""
utils/svg_library.py
─────────────────────
SVG diagram library for StudyAI.

Provides simple, consistent SVG templates for common mathematical diagrams.
Used by the Writer when diagram_block is requested and a standard template
matches the topic.

All SVG strings are valid, self-contained SVG markup.
"""

from __future__ import annotations

# ── Standard diagram templates ─────────────────────────────────────────────────

NORMAL_DISTRIBUTION_CURVE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200" width="400" height="200">
  <style>
    .axis { stroke: #333; stroke-width: 1.5; }
    .curve { stroke: #2563eb; stroke-width: 2.5; fill: none; }
    .area { fill: #2563eb22; }
    .label { font-family: serif; font-size: 12px; fill: #333; }
    .mu { font-family: serif; font-style: italic; font-size: 13px; fill: #2563eb; }
  </style>
  <!-- Axes -->
  <line x1="20" y1="170" x2="380" y2="170" class="axis"/>
  <line x1="200" y1="20" x2="200" y2="175" class="axis" stroke-dasharray="4,4"/>
  <!-- Normal curve approximation -->
  <path d="M 40,168 C 80,168 110,100 140,50 C 160,20 180,10 200,10 C 220,10 240,20 260,50 C 290,100 320,168 360,168 Z" class="area"/>
  <path d="M 40,168 C 80,168 110,100 140,50 C 160,20 180,10 200,10 C 220,10 240,20 260,50 C 290,100 320,168 360,168" class="curve"/>
  <!-- Labels -->
  <text x="197" y="185" class="mu">μ</text>
  <text x="10" y="175" class="label">−3σ</text>
  <text x="355" y="175" class="label">+3σ</text>
</svg>"""


STANDARD_BELL_CURVE = NORMAL_DISTRIBUTION_CURVE  # alias


VENN_TWO_SETS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 200" width="300" height="200">
  <style>
    .set-a { fill: #3b82f655; stroke: #3b82f6; stroke-width: 2; }
    .set-b { fill: #ef444455; stroke: #ef4444; stroke-width: 2; }
    .label { font-family: serif; font-size: 14px; fill: #111; font-weight: bold; }
  </style>
  <circle cx="115" cy="100" r="75" class="set-a"/>
  <circle cx="185" cy="100" r="75" class="set-b"/>
  <text x="80" y="105" class="label">A</text>
  <text x="210" y="105" class="label">B</text>
  <text x="138" y="105" class="label" font-size="11">A∩B</text>
</svg>"""


BAYES_TREE_DIAGRAM = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 200" width="360" height="200">
  <style>
    .branch { stroke: #333; stroke-width: 1.5; fill: none; }
    .node { fill: #2563eb; r: 4; }
    .label { font-family: serif; font-size: 11px; fill: #333; }
  </style>
  <!-- Root -->
  <circle cx="40" cy="100" r="5" fill="#333"/>
  <!-- First branches -->
  <line x1="45" y1="100" x2="150" y2="50" class="branch"/>
  <line x1="45" y1="100" x2="150" y2="150" class="branch"/>
  <!-- Second branches -->
  <line x1="155" y1="50" x2="280" y2="30" class="branch"/>
  <line x1="155" y1="50" x2="280" y2="70" class="branch"/>
  <line x1="155" y1="150" x2="280" y2="130" class="branch"/>
  <line x1="155" y1="150" x2="280" y2="170" class="branch"/>
  <!-- Labels -->
  <text x="80" y="68" class="label">P(A)</text>
  <text x="80" y="138" class="label">P(A')</text>
  <text x="200" y="25" class="label">P(B|A)</text>
  <text x="200" y="68" class="label">P(B'|A)</text>
  <text x="200" y="128" class="label">P(B|A')</text>
  <text x="200" y="168" class="label">P(B'|A')</text>
</svg>"""


_LIBRARY: dict[str, str] = {
    "normal_distribution": NORMAL_DISTRIBUTION_CURVE,
    "bell_curve":          STANDARD_BELL_CURVE,
    "venn_two_sets":       VENN_TWO_SETS,
    "venn_2":              VENN_TWO_SETS,
    "bayes_tree":          BAYES_TREE_DIAGRAM,
    "probability_tree":    BAYES_TREE_DIAGRAM,
}


def get_svg(diagram_type: str) -> str | None:
    """
    Return an SVG string for a named diagram type, or None if not available.
    diagram_type is case-insensitive.
    """
    return _LIBRARY.get(diagram_type.lower().replace(" ", "_"))


def list_available() -> list[str]:
    """Return a sorted list of available diagram type names."""
    return sorted(_LIBRARY.keys())
