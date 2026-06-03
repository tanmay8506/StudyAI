"""Extract text from syllabus PDF to see real units/topics."""
import sys
import subprocess

pdf_path = r"C:\Users\lenovo\tanmay-projects\StudyAi\backend\source_pdfs\2352203601\syllabus.pdf"

# Try pypdf first
try:
    import pypdf
    reader = pypdf.PdfReader(pdf_path)
    print(f"Total pages: {len(reader.pages)}")
    print("=" * 60)
    for i, page in enumerate(reader.pages[:15]):  # First 15 pages
        text = page.extract_text()
        if text and text.strip():
            print(f"\n--- PAGE {i+1} ---")
            print(text[:2000])
        if i >= 14:
            break
except ImportError:
    print("pypdf not installed, trying pdfplumber...")
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            for i, page in enumerate(pdf.pages[:15]):
                text = page.extract_text()
                if text:
                    print(f"\n--- PAGE {i+1} ---")
                    print(text[:2000])
    except ImportError:
        print("Neither pypdf nor pdfplumber installed.")
        print("Try: pip install pypdf")
