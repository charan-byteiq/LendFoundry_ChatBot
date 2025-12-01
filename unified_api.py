import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import google.generativeai as genai
from dotenv import load_dotenv
from uuid import uuid4
import asyncio
import random
from typing import Optional

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Backend URLs
LF_ASSIST_URL = os.getenv("LF_ASSIST_URL", "http://127.0.0.1:8002")
DOC_ASSIST_URL = os.getenv("DOC_ASSIST_URL", "http://127.0.0.1:8003")
DB_ASSIST_URL = os.getenv("DB_ASSIST_URL", "http://127.0.0.1:8001")

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
    session_id: str
    tags: list[str] | None = None

async def classify_query_with_gemini(
    query: str, 
    doc_uploaded: bool,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> str:
    """
    Classifies the query with automatic retry on failure using exponential backoff.
    
    Args:
        query: User's query text
        doc_uploaded: Whether a document was uploaded
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
    
    Returns:
        Classification category string
    """
    prompt = f"""
    You are an intent classifier for a corporate lending company's chatbot system.

    The chatbot's PURPOSE is to:
    - Answer questions about the company's lending policies, procedures, and services
    - Help users understand uploaded loan documents
    - Provide loan status and database information

    Classify the user's query into EXACTLY ONE category:

    1. **company knowledge**
       - Questions about company policies, lending procedures, loan products, fees, contact info
       - How-to questions about using the company's services
       - General information about lending processes
       Examples: "How do I apply for a loan?", "What are your interest rates?", "What documents do I need?"

    2. **document q&a** 
       - Questions specifically about an uploaded document's content
       - ONLY choose this if document IS uploaded
       Examples: "What is the interest rate in this document?", "Summarize this contract","What is the date of birth?"

    3. **database**
       - Queries about specific loan records, customer data, account balances
       - Questions requiring database lookup
       Examples: "What are the number of loans onboarded in last 5 months", "Show loan ID 12345", "How many borrowers have loan amount greater tHAN 20000"

    4. **out_of_scope**
       - General chitchat or greetings (e.g., "hello", "how are you", "good morning")
       - Questions completely unrelated to lending/finance
       - Personal questions about the AI itself
       - Requests for general knowledge, weather, news, entertainment
       Examples: "What's the weather today?", "Tell me a joke", "Who won the game?", "Write me a poem"

    Document uploaded: {str(doc_uploaded).lower()}
    User query: "{query}"

    IMPORTANT RULES:
    - Greetings and pleasantries → out_of_scope
    - Questions unrelated to lending/finance → out_of_scope
    - If document uploaded AND question about the document → document q&a
    - Loan/database specific queries → database
    - Company/policy questions → company knowledge

    Respond with EXACTLY one of: company knowledge, document q&a, database, out_of_scope
    """
    
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            print(f"🔄 Classification attempt {attempt + 1}/{max_retries + 1}")
            
            response = await model.generate_content_async(prompt)
            category = response.text.strip().lower()
            
            # Parse response
            if "out" in category or "scope" in category:
                return "out_of_scope"
            elif "document" in category:
                return "document q&a"
            elif "database" in category:
                return "database"
            elif "company" in category or "knowledge" in category:
                return "company knowledge"
            
            # If we got a response but couldn't parse it, treat as unknown
            print(f"⚠️ Unrecognized category: {category}")
            return "out_of_scope"
            
        except Exception as e:
            last_exception = e
            print(f"⚠️ Gemini classification error (attempt {attempt + 1}/{max_retries + 1}): {e}")
            
            # If this was the last attempt, fall back
            if attempt == max_retries:
                print(f"❌ Max retries reached. Using fallback classification.")
                break
            
            # Calculate exponential backoff delay with jitter
            delay = min(base_delay * (2 ** attempt), 10.0)  # Cap at 10 seconds
            jitter = random.uniform(0, 0.5)  # Add random jitter
            total_delay = delay + jitter
            
            print(f"⏳ Retrying in {total_delay:.2f} seconds...")
            await asyncio.sleep(total_delay)
    
    # Fallback logic if all retries failed
    print(f"⚠️ Falling back to default classification after {max_retries} retries")
    return "out_of_scope"  # Conservative fallback to trigger deflection response



async def generate_deflection_response(query: str) -> str:
    """
    Generates a polite, contextual deflection response for out-of-scope queries.
    Redirects users to the chatbot's purpose without saying "no".
    """
    prompt = f"""
    You are a helpful assistant for a corporate lending company chatbot.

    A user asked: "{query}"

    This question is outside the scope of what you can help with. Your role is to:
    - Answer questions about lending policies, loan products, and procedures
    - Help with uploaded loan documents
    - Provide loan status and account information

    Generate a BRIEF, POLITE response (2-3 sentences max) that:
    1. Acknowledges their question warmly
    2. Gently redirects them to what you CAN help with
    3. NEVER says "no", "can't", "unable", or "not allowed"
    4. Sounds natural and friendly, not robotic

    Examples of GOOD responses:
    - "That's an interesting question! I'm here to help you with loan applications, policies, and account information. Is there anything related to our lending services I can assist you with?"
    - "I appreciate you reaching out! My expertise is in helping customers with loan queries, document reviews, and account details. What can I help you explore about our lending services today?"
    
    Examples of BAD responses:
    - "I cannot answer that question." ❌
    - "That's outside my scope." ❌
    - "I'm not allowed to discuss that." ❌

    Generate your polite deflection response now:
    """
    
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    try:
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Error generating deflection: {e}")
        # Fallback response
        return (
            "I'd love to help you with that! My specialty is assisting with loan applications, "
            "policies, document reviews, and account information. What can I help you with "
            "regarding our lending services today?"
        )


async def call_lf_assist(query: str, session_id: str) -> dict:
    """
    Call LF Assist with session management.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{LF_ASSIST_URL}/chat",
                json={"query": query, "session_id": session_id},
                timeout=30.0
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "answer": data.get("answer", "No answer from LF Assist."),
                "tags": data.get("tags", []),
                "session_id": data.get("session_id", session_id)
            }
        except Exception as e:
            print(f"❌ LF Assist Error: {e}")
            return {"answer": f"LF Assist error: {str(e)}", "tags": [], "session_id": session_id}


async def call_doc_assist(query: str, file: UploadFile) -> str:
    """
    Call Doc Assist with multipart form data.
    """
    try:
        await file.seek(0)
        file_content = await file.read()
        
        async with httpx.AsyncClient() as client:
            files = {
                "question": (None, query),
                "file": (file.filename, file_content, file.content_type or 'application/pdf')
            }
            
            resp = await client.post(
                f"{DOC_ASSIST_URL}/ask/",
                files=files,
                timeout=60.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("answer", "No answer from Doc Assist.")
            
    except Exception as e:
        print(f"❌ Doc Assist Error: {e}")
        return f"Doc Assist error: {str(e)}"


async def call_db_assist(query: str) -> str:
    """
    Call DB Assist with JSON payload.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{DB_ASSIST_URL}/api/chat",
                json={"prompt": query},
                timeout=30.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "No response from DB Assist.")
            
        except Exception as e:
            print(f"❌ DB Assist Error: {e}")
            return f"DB Assist error: {str(e)}"


@app.post("/chat", response_model=ChatResponse)
async def unified_chat(
    message: str = Form(...),
    session_id: str = Form(default=None),
    file: UploadFile | None = File(default=None),
):
    """
    Unified chat endpoint with intelligent scope detection and polite deflection.
    
    Handles four types of queries:
    1. Company knowledge - Routes to LF Assist
    2. Document Q&A - Routes to Doc Assist
    3. Database queries - Routes to DB Assist
    4. Out-of-scope - Generates polite deflection response
    """
    
    # Generate or use existing session_id
    if not session_id:
        session_id = str(uuid4())
        print(f"🆕 New session: {session_id}")
    else:
        print(f"🔄 Continuing session: {session_id}")
    
    doc_uploaded = file is not None
    print(f"📩 Query: '{message}' | Doc: {doc_uploaded}")

    # Step 1: Classify the query
    category = await classify_query_with_gemini(message, doc_uploaded)
    print(f"🎯 Category: {category}")
    
    # Step 2: Handle out-of-scope queries with deflection
    if category == "out_of_scope":
        print("🚫 Out of scope - generating deflection response")
        answer = await generate_deflection_response(message)
        return ChatResponse(
            backend="scope_guard",
            answer=answer,
            session_id=session_id,
            tags=None
        )
    
    # Step 3: Handle edge cases
    if category == "document q&a" and not doc_uploaded:
        print("⚠️ Document Q&A without file - fallback to company knowledge")
        category = "company knowledge"

    # Step 4: Route to appropriate backend
    answer = ""
    backend = ""
    tags = []

    if category == "company knowledge":
        print("→ Routing to LF Assist")
        result = await call_lf_assist(message, session_id)
        answer = result["answer"]
        tags = result.get("tags", [])
        session_id = result.get("session_id", session_id)
        backend = "lf_assist"
        
    elif category == "document q&a":
        print("→ Routing to Doc Assist")
        answer = await call_doc_assist(message, file)
        backend = "doc_assist"
        
    elif category == "database":
        print("→ Routing to DB Assist")
        answer = await call_db_assist(message)
        backend = "db_assist"
        
    else:
        # Fallback
        print("⚠️ Unknown category - fallback to LF Assist")
        result = await call_lf_assist(message, session_id)
        answer = result["answer"]
        tags = result.get("tags", [])
        session_id = result.get("session_id", session_id)
        backend = "lf_assist"

    print(f"✅ Response from {backend}: {answer[:100]}...")
    
    return ChatResponse(
        backend=backend,
        answer=answer,
        session_id=session_id,
        tags=tags if tags else None
    )


@app.post("/chat/clear/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation history for LF Assist session."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{LF_ASSIST_URL}/chat/clear",
                params={"session_id": session_id},
                timeout=10.0
            )
            resp.raise_for_status()
            print(f"🗑️ Cleared session: {session_id}")
            return {"message": f"Session {session_id} cleared", "success": True}
        except Exception as e:
            print(f"❌ Error clearing session: {e}")
            return {"message": f"Error: {str(e)}", "success": False}


@app.get("/health")
async def health_check():
    """Check health of all backend services."""
    health_status = {}
    
    async with httpx.AsyncClient() as client:
        # Check LF Assist
        try:
            await client.get(f"{LF_ASSIST_URL}/chat/sessions", timeout=5.0)
            health_status["lf_assist"] = "healthy"
        except:
            health_status["lf_assist"] = "unhealthy"
        
        # Check Doc Assist
        try:
            await client.get(f"{DOC_ASSIST_URL}/", timeout=5.0)
            health_status["doc_assist"] = "healthy"
        except:
            health_status["doc_assist"] = "unhealthy"
        
        health_status["db_assist"] = "unknown"
        health_status["scope_guard"] = "healthy"
    
    return {"status": health_status}


@app.get("/")
def root():
    return {
        "service": "Unified Chatbot Router",
        "version": "2.0",
        "backends": ["lf_assist", "doc_assist", "db_assist", "scope_guard"],
        "features": ["session_management", "scope_detection", "polite_deflection"]
    }
