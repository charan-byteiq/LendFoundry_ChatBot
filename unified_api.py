import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Backend URLs
LF_ASSIST_URL = os.getenv("LF_ASSIST_URL", "http://127.0.0.1:8002/chat")
DOC_ASSIST_URL = os.getenv("DOC_ASSIST_URL", "http://127.0.0.1:8003/ask/")
DB_ASSIST_URL = os.getenv("DB_ASSIST_URL", "http://127.0.0.1:8001/api/chat")

app = FastAPI(title="Unified Chatbot Router")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatResponse(BaseModel):
    backend: str
    answer: str

async def classify_query_with_gemini(query: str, doc_uploaded: bool) -> str:
    """
    Classifies the query using a prompt heavily biased towards context.
    """
    
    # We explicitly tell the model that if a doc is uploaded, 
    # vague questions usually refer to the document.
    prompt = f"""
    You are a strict intent router for a corporate chatbot. You must route the user's query to exactly one of three backends based on the context.

    ### Context
    Document Uploaded: {str(doc_uploaded).upper()}
    User Query: "{query}"

    ### Categories
    1. **document q&a**
       - USE THIS IF: A document IS uploaded AND the user asks about "this file", "the pdf", "summarize this", or asks for specific details likely contained in the file.
       - CRITICAL: If a document is uploaded and the user asks a generic question (e.g., "What are the terms?", "Explain the fees"), assume they are asking about the DOCUMENT.
       - NOTE: If 'Document Uploaded' is FALSE, you CANNOT choose this category.

    2. **database**
       - USE THIS IF: The user asks about specific loan statuses, loan IDs, repayment schedules, or customer data that would be stored in a dynamic SQL database.
       - Keywords: "loan status", "balance", "how much do I owe", "loan ID #123".

    3. **company knowledge**
       - USE THIS IF: The user asks general questions about the company, policies, contact info, or standard operating procedures that are NOT specific to the uploaded file or a specific loan.
       - Fallback: If the query is general and NO document is uploaded, use this.

    ### Output Instruction
    Analyze the "Document Uploaded" status first.
    Respond with ONLY one of these exact strings:
    company knowledge
    document q&a
    database
    """
    
    # Note: Ensure you are using a valid model name. 
    # 'gemini-1.5-flash' is the current standard. 
    # If you have access to 2.5, keep it, otherwise switch to 1.5-flash.
    model = genai.GenerativeModel('models/gemini-1.5-flash') 
    
    try:
        response = await model.generate_content_async(prompt)
        category = response.text.strip().lower()
    except Exception as e:
        print(f"Gemini Error: {e}")
        # Fallback logic
        return "document q&a" if doc_uploaded else "company knowledge"

    # Clean up response just in case
    if "document" in category:
        return "document q&a"
    elif "database" in category:
        return "database"
    elif "company" in category:
        return "company knowledge"
    
    # Final fallback
    return "document q&a" if doc_uploaded else "company knowledge"

async def call_lf_assist(query: str) -> str:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(LF_ASSIST_URL, json={"query": query}, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            return data.get("answer", "No answer from LF Assist.")
        except Exception as e:
            return f"LF Assist error: {str(e)}"

async def call_doc_assist(query: str, file: UploadFile) -> str:
    try:
        # Reset file cursor to 0 just in case it was read elsewhere
        await file.seek(0)
        file_content = await file.read()
        
        async with httpx.AsyncClient() as client:
            files = {
                "question": (None, query),
                "file": (file.filename, file_content, file.content_type or 'application/pdf')
            }
            # Increased timeout for document processing
            resp = await client.post(DOC_ASSIST_URL, files=files, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            # Handle different capitalization keys
            return data.get("answer") or data.get("Answer") or "No answer from Doc Assist."
    except Exception as e:
        return f"Doc Assist error: {str(e)}"

async def call_db_assist(query: str) -> str:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(DB_ASSIST_URL, json={"prompt": query}, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "No answer from DB Assist.")
        except Exception as e:
            return f"DB Assist error: {str(e)}"

@app.post("/chat", response_model=ChatResponse)
async def unified_chat(
    message: str = Form(...),
    file: UploadFile | None = File(default=None),
):
    doc_uploaded = file is not None

    # 1. Classify
    category = await classify_query_with_gemini(message, doc_uploaded)
    
    # 2. Logic to handle "Impossible" cases
    # If Gemini hallucinated "document q&a" but no file is there, force fallback
    if category == "document q&a" and not doc_uploaded:
        category = "company knowledge"

    # 3. Route
    answer = ""
    backend = ""

    if category == "company knowledge":
        answer = await call_lf_assist(message)
        backend = "lf_assist"
    elif category == "document q&a":
        answer = await call_doc_assist(message, file)
        backend = "doc_assist"
    elif category == "database":
        answer = await call_db_assist(message)
        backend = "db_assist"
    else:
        # Fallback
        answer = await call_lf_assist(message)
        backend = "lf_assist"

    return ChatResponse(backend=backend, answer=answer)
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))



# Backend URLs - replace with your actual endpoints or load from config
LF_ASSIST_URL = os.getenv("LF_ASSIST_URL", "http://127.0.0.1:8002/chat")
DOC_ASSIST_URL = os.getenv("DOC_ASSIST_URL", "http://127.0.0.1:8003/ask/")
DB_ASSIST_URL = os.getenv("DB_ASSIST_URL", "http://127.0.0.1:8001/api/chat")

app = FastAPI(title="Unified Chatbot Router")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production restrict origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    backend: str
    answer: str

async def classify_query_with_gemini(query: str, doc_uploaded: bool) -> str:
    """
    Call Gemini 2.5 Flash to classify the query into one of:
    'company knowledge', 'document Q&A', or 'database'.
    """
    prompt = f"""
            You are an intent classifier for a company chatbot system with three assistants.

            Possible categories:
            1. company knowledge - Classify the question into this category if the user seems to be asking to know about the company. 
            Basically you can classify any question that a company manual can answer into this category. Questions answered by LF Assist. 
            2. document Q&A - Classify the question into this category if the user is asking specific questions about any uploaded document.
            Questions answered by Doc Assist about the uploaded document.
            3. database - Classify the question into this category if the user asks questions related to a database. 
            The database contains information about loans and details of the loans. Questions answered by DB Assist querying company database.

            Document uploaded: {str(doc_uploaded).lower()}

            User question: {query}

            Respond only with exactly one category label among: company knowledge, document Q&A, database.
            """
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    response = model.generate_content([prompt])
    category = response.text.strip().lower()

    if category not in {"company knowledge", "document q&a", "database"}:
        # Fallback or unknown classification
        category = "company knowledge"
    return category

async def call_lf_assist(query: str) -> str:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(LF_ASSIST_URL, json={"query": query})
            resp.raise_for_status()
            data = resp.json()
            return data.get("answer", "No answer from LF Assist.")
        except Exception as e:
            return f"LF Assist error: {str(e)}"

async def call_doc_assist(query: str, file: UploadFile) -> str:
    """
    Sends multipart/form-data with query and pdf file to Doc Assist.
    """
    try:
        file_content = await file.read()
        async with httpx.AsyncClient() as client:
            files = {
                "question": (None, query),
                "file": (file.filename, file_content, file.content_type or 'application/pdf')
            }
            resp = await client.post(DOC_ASSIST_URL, files=files)
            resp.raise_for_status()
            data = resp.json()
            return data.get("answer") or data.get("Answer") or "No answer from Doc Assist."
    except Exception as e:
        return f"Doc Assist error: {str(e)}"

async def call_db_assist(query: str) -> str:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(DB_ASSIST_URL, json={"prompt": query})
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "No answer from DB Assist.")
        except Exception as e:
            return f"DB Assist error: {str(e)}"

@app.post("/chat", response_model=ChatResponse)
async def unified_chat(
    message: str = Form(...),
    file: UploadFile | None = File(default=None),
):
    """
    Unified chat endpoint that:
    1. Checks if document is uploaded and flags that for classification.
    2. Calls Gemini LLM for routing decision.
    3. Routes to correct backend and returns response.
    """
    doc_uploaded = file is not None

    category = await classify_query_with_gemini(message, doc_uploaded)

    if category == "company knowledge":
        answer = await call_lf_assist(message)
        backend = "lf_assist"
    elif category == "document q&a" and doc_uploaded:
        answer = await call_doc_assist(message, file)
        backend = "doc_assist"
    elif category == "database":
        answer = await call_db_assist(message)
        backend = "db_assist"
    else:
        # Fallback if doc Q&A without file
        if doc_uploaded:
            # If doc is uploaded but not classified correctly - fallback to doc assist
            answer = await call_doc_assist(message, file)
            backend = "doc_assist"
        else:
            # Otherwise fallback to company knowledge
            answer = await call_lf_assist(message)
            backend = "lf_assist"

    return ChatResponse(backend=backend, answer=answer)
