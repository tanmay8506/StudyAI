import fitz

pdf_path = r"C:\Users\lenovo\tanmay-projects\StudyAi\backend\source_pdfs\2352203601\syllabus.pdf"

try:
    doc = fitz.open(pdf_path)
    print("Metadata:", doc.metadata)
    print("Page count:", len(doc))
    for i, page in enumerate(doc):
        print(f"\n--- Page {i+1} ---")
        print("Rect:", page.rect)
        print("Text len:", len(page.get_text()))
        print("Images:", len(page.get_images()))
        print("XObjects:")
        for x in page.get_drawings():
            print("Drawing:", x.get("type"), len(x.get("items", [])))
except Exception as e:
    print("Error:", e)
