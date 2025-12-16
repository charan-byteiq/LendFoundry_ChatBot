import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
from uuid import uuid4
import asyncio
import random
from typing import Optional, Any, Dict, List

# Import all routers
from lf_assist.app.api import router as lf_assist_router, process_lf_chat, clear_conversation
from new.api import router as doc_assist_router, process_pdf_question
from src.api import router as db_assist_router, process_db_query
from viz_assist.api import router as viz_assist_router, process_viz_query, VizChatbotService

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Lifespan Event Handler ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    # Startup: Initialize visualization chatbot service
    print(" Initializing Visualization Chatbot Service...")
    viz_service = VizChatbotService.get_instance()
    viz_service.initialize()
    print(" All services initialized")
    
    yield
    
    # Shutdown
    print(" Shutting down Unified Chatbot API")

# Create app with lifespan
app = FastAPI(
    title="Unified Chatbot Router",
    description="Unified API for LF Assist, Doc Assist, DB Assist, and Visualization Assist",
    version="3.1",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all backend routers
app.include_router(lf_assist_router)
app.include_router(doc_assist_router)
app.include_router(db_assist_router)
app.include_router(viz_assist_router)


class ChatResponse(BaseModel):
    backend: str
    answer: str
    session_id: str
    tags: Optional[List[str]] = None
    data: Optional[List[Dict[str, Any]]] = None
    sql_query: Optional[str] = None
    chart_analysis: Optional[Dict[str, Any]] = None
    record_count: Optional[int] = None
    error: Optional[str] = None

# Classification Logic 

async def classify_query_with_gemini(
    query: str,
    doc_uploaded: bool,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> str:
    """Classifies the query with automatic retry - now includes visualization category"""
    prompt = f"""
    You are an intent classifier for a corporate lending company's chatbot system.

    The chatbot's PURPOSE is to:
    - Answer questions about the company's lending policies, procedures, and services
    - Help users understand uploaded loan documents
    - Provide loan status and database information
    - Create visualizations and charts from database data

    Classify the user's query into EXACTLY ONE category:

    1. **company knowledge**
       - Questions about company policies, lending procedures, loan products, fees, contact info
       - How-to questions about using the company's services
       - General information about lending processes
       Examples: "How do I apply for a loan?", "What are your interest rates?", "What documents do I need?"

    2. **document q&a** 
       - Questions specifically about an uploaded document's content
       - ONLY choose this if document IS uploaded
       Examples: "What is the interest rate in this document?", "Summarize this contract"

    3. **database**
       - Simple queries about specific loan records, customer data, account balances
       - Questions requiring database lookup WITHOUT visualization
       - Requests for raw data or specific records
       Examples: "Show loan ID 12345", "What is the status of my loan?", "How many active loans?"

    4. **visualization**
       - Queries that request charts, graphs, or visual representations of data
       - Analytical questions requiring data aggregation and visualization
       - Trend analysis, comparisons, or distribution questions
       - Any question with keywords like: chart, graph, plot, visualize, show trend, compare, distribution
       Examples: "Show me a chart of loan amounts", "Plot monthly loan trends", "Visualize loan distribution by state", 
                 "Compare interest rates across products", "Graph the number of loans per month"

    5. **out_of_scope**
       - General chitchat or greetings (e.g., "hello", "how are you")
       - Questions completely unrelated to lending/finance
       - Personal questions about the AI itself
       Examples: "What's the weather today?", "Tell me a joke"

    Document uploaded: {str(doc_uploaded).lower()}
    User query: "{query}"

    IMPORTANT RULES:
    - Keywords like "chart", "graph", "plot", "visualize", "trend", "compare" → visualization
    - Simple data queries without visualization keywords → database
    - Greetings and pleasantries → out_of_scope
    - If document uploaded AND question about the document → document q&a
    - Company/policy questions → company knowledge

    Respond with EXACTLY one of: company knowledge, document q&a, database, visualization, out_of_scope
    """
    
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    for attempt in range(max_retries + 1):
        try:
            print(f"🔄 Classification attempt {attempt + 1}/{max_retries + 1}")
            
            response = await model.generate_content_async(prompt)
            category = response.text.strip().lower()
            
            # Parse response
            if "visualization" in category or "visualize" in category:
                return "visualization"
            elif "out" in category or "scope" in category:
                return "out_of_scope"
            elif "document" in category:
                return "document q&a"
            elif "database" in category:
                return "database"
            elif "company" in category or "knowledge" in category:
                return "company knowledge"
            
            print(f" Unrecognized category: {category}")
            return "out_of_scope"
            
        except Exception as e:
            print(f" Gemini classification error (attempt {attempt + 1}/{max_retries + 1}): {e}")
            
            if attempt == max_retries:
                print(f" Max retries reached. Using fallback classification.")
                break
            
            delay = min(base_delay * (2 ** attempt), 10.0)
            jitter = random.uniform(0, 0.5)
            total_delay = delay + jitter
            
            print(f" Retrying in {total_delay:.2f} seconds...")
            await asyncio.sleep(total_delay)
    
    print(f" Falling back to default classification")
    return "out_of_scope"

async def generate_deflection_response(query: str) -> str:
    """Generates a polite deflection response for out-of-scope queries"""
    prompt = f"""
    You are a helpful assistant for a corporate lending company chatbot.

    A user asked: "{query}"

    This question is outside the scope of what you can help with. Your role is to:
    - Answer questions about lending policies, loan products, and procedures
    - Help with uploaded loan documents
    - Provide loan status and account information
    - Create data visualizations and charts

    Generate a BRIEF, POLITE response (2-3 sentences max) that:
    1. Acknowledges their question warmly
    2. Gently redirects them to what you CAN help with
    3. NEVER says "no", "can't", "unable", or "not allowed"
    4. Sounds natural and friendly

    Generate your polite deflection response now:
    """
    
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    try:
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        print(f" Error generating deflection: {e}")
        return (
            "I'd love to help you with that! My specialty is assisting with loan applications, "
            "policies, document reviews, account information, and data visualizations. "
            "What can I help you with regarding our lending services today?"
        )

# --- Main Unified Chat Endpoint ---

@app.post("/chat", response_model=ChatResponse)
async def unified_chat(
    message: str = Form(...),
    session_id: str = Form(default=None),
    file: UploadFile | None = File(default=None),
):
    """
    Unified chat endpoint with intelligent routing to 4 backends + visualization support.
    """
    
    # Generate or use existing session_id
    if not session_id:
        session_id = str(uuid4())
        print(f" New session: {session_id}")
    else:
        print(f" Continuing session: {session_id}")
    
    doc_uploaded = file is not None
    print(f" Query: '{message}' | Doc: {doc_uploaded}")

    # Step 1: Classify the query
    category = await classify_query_with_gemini(message, doc_uploaded)
    print(f" Category: {category}")
    
    # Step 2: Handle out-of-scope queries
    if category == "out_of_scope":
        print(" Out of scope - generating deflection response")
        answer = await generate_deflection_response(message)
        return ChatResponse(
            backend="scope_guard",
            answer=answer,
            session_id=session_id,
            tags=None
        )
    
    # Step 3: Handle edge cases
    if category == "document q&a" and not doc_uploaded:
        print(" Document Q&A without file - fallback to llM")
        category = "out_of_scope"

    # Step 4: Route to appropriate backend (direct function calls)
    answer = ""
    backend = ""
    tags = []
    data = None
    sql_query = None
    chart_analysis = None

    if category == "company knowledge":
        print("→ Routing to LF Assist")
        result = await process_lf_chat(message, session_id)
        answer = result.answer
        tags = result.tags
        backend = "lf_assist"
        
    elif category == "document q&a":
        print("→ Routing to Doc Assist")
        file_content = await file.read()
        answer = await process_pdf_question(message, file_content, file.filename)
        backend = "doc_assist"
        
    elif category == "database":
        print("→ Routing to DB Assist")
        result = await process_db_query(message)
        answer = result["response"]
        backend = "db_assist"
        if not result.get("success", True):
             # If success is explicitly False, we can flag it, 
             # though usually the error message is in 'answer'
             pass
    
    elif category == "visualization":
        print("→ Routing to Visualization Assist")
        result = await process_viz_query(message, session_id)
        
        if result.error:
            answer = f"Visualization Error: {result.error}"
        else:
            answer = f"Query executed successfully. Retrieved {result.record_count} records."
            if result.chart_analysis and result.chart_analysis.chartable:
                answer += f" Chart type: {result.chart_analysis.auto_chart.type if result.chart_analysis.auto_chart else 'N/A'}"
        
        data = result.data
        sql_query = result.sql_query
        chart_analysis = result.chart_analysis.dict() if result.chart_analysis else None
        backend = "viz_assist"
        
    else:
        # Fallback
        print(" Unknown category - fallback to LF Assist")
        result = await process_lf_chat(message, session_id)
        answer = result.answer
        tags = result.tags
        backend = "lf_assist"

    print(f" Response from {backend}: {answer[:100]}...")
    
    return ChatResponse(
        backend=backend,
        answer=answer,
        session_id=session_id,
        tags=tags if tags else None,
        data=data,
        sql_query=sql_query,
        chart_analysis=chart_analysis,
        record_count=len(data) if data else None,
        error=result.error if backend == "viz_assist" and hasattr(result, "error") else None
    )

# --- Utility Endpoints ---

@app.post("/chat/clear/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation history for LF Assist session"""
    try:
        clear_conversation(session_id)
        print(f" Cleared session: {session_id}")
        return {"message": f"Session {session_id} cleared", "success": True}
    except Exception as e:
        print(f" Error clearing session: {e}")
        return {"message": f"Error: {str(e)}", "success": False}

@app.get("/health")
async def health_check():
    """Check health of all backend services"""
    viz_service = VizChatbotService.get_instance()
    
    return {
        "status": {
            "lf_assist": "healthy",
            "doc_assist": "healthy",
            "db_assist": "healthy",
            "viz_assist": "healthy" if viz_service.is_ready() else "initializing",
            "scope_guard": "healthy"
        },
        "message": "All backends integrated internally"
    }

@app.get("/")
def root():
    return {
        "service": "Unified Chatbot Router",
        "version": "3.1",
        "backends": ["lf_assist", "doc_assist", "db_assist", "viz_assist", "scope_guard"],
        "features": [
            "session_management",
            "scope_detection",
            "polite_deflection",
            "integrated_backends",
            "visualization_support"
        ],
        "endpoints": {
            "unified": "/chat",
            "lf_assist": "/lf-assist/chat",
            "doc_assist": "/doc-assist/ask",
            "db_assist": "/db-assist/chat",
            "viz_assist": "/viz-assist/chat"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("unified_api:app", host="0.0.0.0", port=8000, reload=True)
