import os
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

pdf_path = r"C:\Users\lenovo\tanmay-projects\StudyAi\backend\source_pdfs\2352203601\syllabus.pdf"

print("Uploading file to Gemini File API...")
try:
    file_ref = genai.upload_file(path=pdf_path, mime_type="application/pdf")
    print(f"Uploaded successfully. Name: {file_ref.name}, URI: {file_ref.uri}")
    
    # Prompting Gemini 2.0 Flash or 2.5 Pro to extract the syllabus
    # Using gemini-flash-latest because it is very fast and capable
    model = genai.GenerativeModel(model_name="gemini-flash-latest")
    
    prompt = """
    Please read the uploaded syllabus PDF and extract all units, unit names, and the topics listed under each unit.
    Provide the response in structured JSON format matching this schema:
    {
      "units": [
        {
          "unit_number": int,
          "unit_name": str,
          "topics": [str, str, ...],
          "hours": float
        }
      ],
      "prescribed_books": [str]
    }
    """
    
    print("Generating content from PDF using gemini-2.0-flash...")
    response = model.generate_content(
        [file_ref, prompt],
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json"
        )
    )
    print("Response:")
    print(response.text)
    
    # Clean up the file
    print("Deleting file from File API...")
    genai.delete_file(file_ref.name)
    print("Done.")

except Exception as e:
    print(f"An error occurred: {e}")
