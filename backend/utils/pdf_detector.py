"""
utils/pdf_detector.py
──────────────────────
Detects PDF characteristics from a file path.
Used to determine if a PDF is scanned (image-based) vs text-based.
"""

from __future__ import annotations

from pathlib import Path


def is_scanned_pdf(pdf_path: Path) -> bool:
    """
    Heuristic: attempt to extract a small amount of text.
    If less than 50 chars returned, treat as scanned/image-based.
    Falls back to False (text-based) if libraries unavailable.
    """
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            if not pdf.pages:
                return True
            text = pdf.pages[0].extract_text() or ""
            return len(text.strip()) < 50
    except Exception:
        pass

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        if not doc.page_count:
            return True
        text = doc[0].get_text()
        return len(text.strip()) < 50
    except Exception:
        pass

    return False  # Assume text-based if no library available
