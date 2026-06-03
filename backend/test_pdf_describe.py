import os
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

pdf_path = r"C:\Users\lenovo\tanmay-projects\StudyAi\backend\source_pdfs\2352203601\syllabus.pdf"

try:
    file_ref = genai.upload_file(path=pdf_path, mime_type="application/pdf")
    print(f"Uploaded successfully. Name: {file_ref.name}")
    
    model = genai.GenerativeModel(model_name="gemini-flash-latest")
    
    prompt = "Please describe what this PDF is. Read it and summarize its contents page-by-page. What units, topics, or headings are visible? Be descriptive."
    
    print("Generating description...")
    response = model.generate_content([file_ref, prompt])
    print("\n=== DESCRIPTION ===")
    print(response.text)
    
    # Clean up the file
    genai.delete_file(file_ref.name)
    print("Done.")

except Exception as e:
    print(f"An error occurred: {e}")
