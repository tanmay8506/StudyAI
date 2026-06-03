"""
utils/latex_formatter.py
─────────────────────────
LaTeX auto-fixer.  Catches the most common unicode → LaTeX mistakes
that AI models produce.  Applied to every Writer output before DB write
and before Critic scoring.
"""

import re
import logging
from typing import Any

log = logging.getLogger(__name__)

# ── Unicode → LaTeX replacements ─────────────────────────────────────────────
_UNICODE_TO_LATEX: list[tuple[str, str]] = [
    # Greek letters
    ("α", r"\alpha"),   ("β", r"\beta"),    ("γ", r"\gamma"),
    ("δ", r"\delta"),   ("ε", r"\varepsilon"), ("ζ", r"\zeta"),
    ("η", r"\eta"),     ("θ", r"\theta"),   ("ι", r"\iota"),
    ("κ", r"\kappa"),   ("λ", r"\lambda"),  ("μ", r"\mu"),
    ("ν", r"\nu"),      ("ξ", r"\xi"),      ("π", r"\pi"),
    ("ρ", r"\rho"),     ("σ", r"\sigma"),   ("τ", r"\tau"),
    ("υ", r"\upsilon"), ("φ", r"\phi"),     ("χ", r"\chi"),
    ("ψ", r"\psi"),     ("ω", r"\omega"),
    # Capital Greek
    ("Γ", r"\Gamma"),   ("Δ", r"\Delta"),   ("Θ", r"\Theta"),
    ("Λ", r"\Lambda"),  ("Ξ", r"\Xi"),      ("Π", r"\Pi"),
    ("Σ", r"\Sigma"),   ("Υ", r"\Upsilon"), ("Φ", r"\Phi"),
    ("Ψ", r"\Psi"),     ("Ω", r"\Omega"),
    # Number sets
    ("ℝ", r"\mathbb{R}"), ("ℕ", r"\mathbb{N}"), ("ℚ", r"\mathbb{Q}"),
    ("ℤ", r"\mathbb{Z}"), ("ℂ", r"\mathbb{C}"),
    # Common symbols
    ("∞", r"\infty"),  ("≤", r"\leq"),  ("≥", r"\geq"),
    ("≠", r"\neq"),    ("≈", r"\approx"), ("∈", r"\in"),
    ("∉", r"\notin"),  ("⊂", r"\subset"), ("⊆", r"\subseteq"),
    ("∪", r"\cup"),    ("∩", r"\cap"),   ("∅", r"\emptyset"),
    ("→", r"\to"),     ("↔", r"\leftrightarrow"), ("⇒", r"\Rightarrow"),
    ("⇔", r"\Leftrightarrow"), ("√", r"\sqrt"),
    ("×", r"\times"),  ("÷", r"\div"),   ("·", r"\cdot"),
    ("±", r"\pm"),     ("∓", r"\mp"),
    ("∑", r"\sum"),    ("∏", r"\prod"),  ("∫", r"\int"),
    ("∂", r"\partial"), ("∇", r"\nabla"),
    ("∀", r"\forall"), ("∃", r"\exists"),
    ("…", r"\ldots"),  ("·", r"\cdot"),
]

# ── String fields that may contain LaTeX ─────────────────────────────────────
_STRING_FIELDS = {
    "definition", "core_concept", "analogy", "examiners_note",
    "rapid_revision",
}

_NESTED_STRING_PATHS: list[list[str]] = [
    ["rapid_revision", "definition_one_line"],
    ["rapid_revision", "key_formula_or_concept"],
    ["rapid_revision", "examiner_pattern"],
]


def _fix_string(text: str) -> str:
    """Replace bare unicode math symbols with $\\latex$ equivalents."""
    if not text:
        return text
    for unicode_char, latex_cmd in _UNICODE_TO_LATEX:
        if unicode_char in text:
            # Wrap in $ only if not already inside a math context
            # Simple heuristic: if surrounded by $...$, skip
            text = _safe_replace(text, unicode_char, latex_cmd)
    return text


def _safe_replace(text: str, char: str, replacement: str) -> str:
    """Replace char with $replacement$ only when not already inside $...$."""
    result = []
    in_math = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == '$':
            # Toggle math mode (handle $$ as well)
            if i + 1 < len(text) and text[i + 1] == '$':
                in_math = not in_math
                result.append('$$')
                i += 2
                continue
            in_math = not in_math
            result.append(c)
        elif c == char and not in_math:
            result.append(f"${replacement}$")
        else:
            result.append(c)
        i += 1
    return ''.join(result)


def auto_fix_latex(result: dict) -> dict:
    """
    Walk the Writer output dict and replace bare unicode math symbols
    with LaTeX equivalents wrapped in $...$.

    Modifies only string-valued fields — does not touch lists or nested
    objects except for known paths listed in _NESTED_STRING_PATHS.

    Returns the modified dict (in-place modification, also returned for
    chaining convenience).
    """
    if not isinstance(result, dict):
        return result

    for field in _STRING_FIELDS:
        val = result.get(field)
        if isinstance(val, str):
            result[field] = _fix_string(val)

    for path in _NESTED_STRING_PATHS:
        obj = result
        for key in path[:-1]:
            obj = obj.get(key) or {}
            if not isinstance(obj, dict):
                break
        else:
            leaf = path[-1]
            if isinstance(obj.get(leaf), str):
                obj[leaf] = _fix_string(obj[leaf])

    return result
