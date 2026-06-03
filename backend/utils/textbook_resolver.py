"""
utils/textbook_resolver.py
───────────────────────────
Resolves a paper's primary textbook from the UPC registry or
falls back to the prescribed_books list from the syllabus.
"""

from __future__ import annotations

# ── Common DU textbook mapping (short → canonical) ────────────────────────────
_TEXTBOOK_ALIASES: dict[str, str] = {
    "devore":       "Devore, Jay L. (2016). Probability and Statistics for Engineering and the Sciences (9th ed.). Cengage Learning.",
    "bartle":       "Bartle, R.G. & Sherbert, D.R. (2011). Introduction to Real Analysis (4th ed.). Wiley.",
    "rudin":        "Rudin, W. (1976). Principles of Mathematical Analysis (3rd ed.). McGraw-Hill.",
    "apostol":      "Apostol, T.M. (1974). Mathematical Analysis (2nd ed.). Addison-Wesley.",
    "kreyszig":     "Kreyszig, E. (2011). Advanced Engineering Mathematics (10th ed.). Wiley.",
    "gallian":      "Gallian, J.A. (2017). Contemporary Abstract Algebra (9th ed.). Cengage.",
    "herstein":     "Herstein, I.N. (1975). Topics in Algebra (2nd ed.). Wiley.",
    "dummit":       "Dummit, D.S. & Foote, R.M. (2004). Abstract Algebra (3rd ed.). Wiley.",
    "artin":        "Artin, M. (2011). Algebra (2nd ed.). Pearson.",
    "royden":       "Royden, H.L. (1988). Real Analysis (3rd ed.). Macmillan.",
    "folland":      "Folland, G.B. (1999). Real Analysis (2nd ed.). Wiley.",
}


def resolve_primary_textbook(
    prescribed_books: list[str] | None,
    paper_meta: dict | None = None,
) -> str | None:
    """
    Return the canonical primary textbook string for a paper.

    Resolution order:
      1. paper_meta["primary_textbook"] if set (from upc_registry.json)
      2. First book in prescribed_books list
      3. None (Writer uses generic source attribution)
    """
    if paper_meta:
        tb = paper_meta.get("primary_textbook")
        if tb:
            return tb

    if prescribed_books:
        first = prescribed_books[0] if prescribed_books else None
        if first:
            return first

    return None


def lookup_alias(short_name: str) -> str | None:
    """Look up a canonical textbook by short author name."""
    return _TEXTBOOK_ALIASES.get(short_name.strip().lower())
