from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field
from google.genai.types import Content, Part, Blob  # Required types for PDF handling
import PyPDF2
import io
from services import get_gemini_client


router = APIRouter(prefix="/doc-assist", tags=["Doc Assist"])


# =============================================
# REQUEST/RESPONSE SCHEMAS
# =============================================

class DocAssistResponse(BaseModel):
    """Response from document Q&A endpoint"""
    answer: str = Field(..., description="The AI-generated answer based on the uploaded document")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "According to the document, the interest rate is 5.5% APR with a 30-year term..."
            }
        }


class DocAssistRootResponse(BaseModel):
    """Response for doc-assist root endpoint"""
    message: str = Field(..., description="Welcome message")

    class Config:
        json_schema_extra = {
            "example": {"message": "Welcome to the Doc Assist API"}
        }


class HTTPErrorResponse(BaseModel):
    """Error response schema"""
    detail: str = Field(..., description="Error description")

    class Config:
        json_schema_extra = {
            "example": {"detail": "Invalid file type. Please upload a PDF."}
        }


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
    
    # Call Gemini API with proper Content/Part/Blob structure
    gemini = get_gemini_client()
    content = Content(
        parts=[
            Part(text=question),
            Part(inline_data=Blob(mime_type="application/pdf", data=file_content))
        ]
    )
    try:
        response = gemini.generate_content([content])
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {e}")

# Router endpoint
@router.post(
    "/ask",
    response_model=DocAssistResponse,
    responses={
        200: {
            "description": "Successfully answered question about the document",
            "model": DocAssistResponse
        },
        400: {
            "description": "Bad request - Invalid file or validation error",
            "model": HTTPErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_type": {
                            "summary": "Invalid file type",
                            "value": {"detail": "Invalid file type. Please upload a PDF."}
                        },
                        "too_many_pages": {
                            "summary": "Too many pages",
                            "value": {"detail": "PDF exceeds the 20-page limit."}
                        },
                        "file_too_large": {
                            "summary": "File too large",
                            "value": {"detail": "File size exceeds the 5MB limit."}
                        },
                        "corrupted": {
                            "summary": "Corrupted PDF",
                            "value": {"detail": "Could not read the PDF file. It may be corrupted."}
                        }
                    }
                }
            }
        },
        500: {
            "description": "Internal server error - Gemini API error",
            "model": HTTPErrorResponse
        }
    },
    summary="Ask Question About Document",
    description="""
    Upload a PDF document and ask a question about its contents.
    
    ## Limitations
    - **File type**: PDF only
    - **File size**: Maximum 5MB
    - **Page count**: Maximum 20 pages
    
    ## Examples
    - "What is the interest rate in this document?"
    - "Summarize the key terms of this contract"
    - "What are the payment terms?"
    
    ## Request Format
    Send as `multipart/form-data` with:
    - `question`: Your natural language question
    - `file`: The PDF file to analyze
    """
)
async def ask_question(
    question: str = Form(
        ..., 
        description="The question to ask about the uploaded document",
        examples=["What is the interest rate?"]
    ),
    file: UploadFile = File(
        ..., 
        description="PDF file to analyze (max 5MB, 20 pages)"
    )
) -> DocAssistResponse:
    """
    Accepts a question and a PDF file, validates them, and returns an answer.
    """
    if not file.content_type == "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")
    
    file_content = await file.read()
    answer = await process_pdf_question(question, file_content, file.filename)
    
    return DocAssistResponse(answer=answer)


@router.get(
    "/",
    response_model=DocAssistRootResponse,
    summary="API Root",
    description="Returns a welcome message for the Doc Assist API"
)
async def doc_assist_root() -> DocAssistRootResponse:
    return DocAssistRootResponse(message="Welcome to the Doc Assist API")
