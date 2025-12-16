from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import google.generativeai as genai
import os
from dotenv import load_dotenv
import PyPDF2
import io

# Configuration
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable is not set.")

genai.configure(api_key=api_key)

# Create router instead of app
router = APIRouter(prefix="/doc-assist", tags=["Doc Assist"])

# Core logic extracted as callable function
async def process_pdf_question(question: str, file_content: bytes, filename: str = "document.pdf") -> str:
    """
    Core Doc Assist logic - can be called directly from unified API
    """
    # Validate PDF
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        if len(pdf_reader.pages) > 20:
            raise HTTPException(status_code=400, detail="PDF exceeds the 20-page limit.")
    except PyPDF2.errors.PdfReadError:
        raise HTTPException(status_code=400, detail="Could not read the PDF file. It may be corrupted.")
    
    # Check file size (5 MB limit)
    if len(file_content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the 5MB limit.")
    
    # Call Gemini API
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    pdf_part = {"mime_type": "application/pdf", "data": file_content}
    
    try:
        response = model.generate_content([question, pdf_part])
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred with the Gemini API: {e}")

# Router endpoint
@router.post("/ask")
async def ask_question(
    question: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Accepts a question and a PDF file, validates them, and returns an answer.
    """
    if not file.content_type == "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")
    
    file_content = await file.read()
    answer = await process_pdf_question(question, file_content, file.filename)
    
    return {"answer": answer}

@router.get("/")
async def doc_assist_root():
    return {"message": "Welcome to the Doc Assist API"}
