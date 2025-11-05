
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
import PyPDF2
import io

# --- Configuration ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable is not set.")

genai.configure(api_key=api_key)

app = FastAPI(title="PDF Chatbot API")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper Functions ---
def get_gemini_response(question: str, pdf_content: bytes):
    """Sends the user's question and PDF content to the Gemini API."""
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    pdf_part = {"mime_type": "application/pdf", "data": pdf_content}
    
    try:
        response = model.generate_content([question, pdf_part])
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred with the Gemini API: {e}")

# --- API Endpoints ---
@app.post("/ask/")
async def ask_question(
    question: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Accepts a question and a PDF file, validates them, and returns an answer.
    """
    if not file.content_type == "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")

    pdf_content = await file.read()

    # Check file size (e.g., 5 MB limit)
    if len(pdf_content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the 5MB limit.")

    # Check page count
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        if len(pdf_reader.pages) > 20:
            raise HTTPException(status_code=400, detail="PDF exceeds the 20-page limit.")
    except PyPDF2.errors.PdfReadError:
        raise HTTPException(status_code=400, detail="Could not read the PDF file. It may be corrupted.")

    answer = get_gemini_response(question, pdf_content)
    
    return {"answer": answer}

@app.get("/")
def read_root():
    return {"message": "Welcome to the PDF Chatbot API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
