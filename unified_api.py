import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Path, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from uuid import uuid4
import asyncio
import random
from typing import Optional, Any, Dict, List, Literal
from enum import Enum
from logger import logger
from services import get_gemini_client
from redshift_logger import safe_log_to_redshift    
from fastapi import Request
from fastapi.exceptions import RequestValidationError

# Import all routers
from lf_assist.app.api import router as lf_assist_router, process_lf_chat, clear_conversation
from new.api import router as doc_assist_router, process_pdf_question
from src.api import router as db_assist_router, process_db_query
from viz_assist.api import router as viz_assist_router, process_viz_query, VizChatbotService

load_dotenv()
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Lifespan Event Handler ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    # Startup: Initialize visualization chatbot service
    logger.info("Initializing Visualization Chatbot Service...")
    viz_service = VizChatbotService.get_instance()
    viz_service.initialize()
    logger.info("All services initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Unified Chatbot API")

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


# =============================================
# EXCEPTION HANDLERS (Log 422/4xx/5xx errors)
# =============================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log 422 validation errors"""
    safe_log_to_redshift(
        session_id=None,
        chatbot="router",
        user_message=None,
        answer=None,
        response_payload=None,
        is_error=True,
        error_message=str(exc),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Log explicit HTTP exceptions (4xx/5xx)"""
    safe_log_to_redshift(
        session_id=None,
        chatbot="router",
        user_message=None,
        answer=None,
        response_payload=None,
        is_error=True,
        error_message=str(exc.detail),
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unhandled 500 errors"""
    safe_log_to_redshift(
        session_id=None,
        chatbot="router",
        user_message=None,
        answer=None,
        response_payload=None,
        is_error=True,
        error_message=str(exc),
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# =============================================
# ENUMS & TYPE DEFINITIONS
# =============================================

class BackendType(str, Enum):
    """The backend service that handled the request"""
    LF_ASSIST = "lf_assist"
    DOC_ASSIST = "doc_assist"
    DB_ASSIST = "db_assist"
    VIZ_ASSIST = "viz_assist"
    SCOPE_GUARD = "scope_guard"


class ChartType(str, Enum):
    """Supported chart types for visualization"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    HISTOGRAM = "histogram"


# =============================================
# NESTED RESPONSE SCHEMAS
# =============================================

class ChartConfig(BaseModel):
    """Configuration for auto-generated charts (viz_assist only)"""
    type: ChartType = Field(..., description="The type of chart to render")
    title: str = Field(..., description="Title to display on the chart")
    x_axis: Optional[str] = Field(None, description="Data key to use for X-axis")
    y_axis: Optional[str] = Field(None, description="Data key to use for Y-axis")
    reason: Optional[str] = Field(None, description="Why this chart type was chosen")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "bar",
                "title": "Loan Distribution by State",
                "x_axis": "state",
                "y_axis": "loan_count",
                "reason": "Bar chart best shows categorical comparisons"
            }
        }


class ChartAnalysis(BaseModel):
    """Chart analysis result from viz_assist backend"""
    chartable: bool = Field(..., description="Whether the data can be visualized as a chart")
    reasoning: Optional[str] = Field(None, description="Explanation for chartability decision")
    auto_chart: Optional[ChartConfig] = Field(None, description="Auto-recommended chart configuration")
    suggested_charts: Optional[List[Dict[str, Any]]] = Field(None, description="Alternative chart suggestions")

    class Config:
        json_schema_extra = {
            "example": {
                "chartable": True,
                "reasoning": "Data has categorical X values and numeric Y values",
                "auto_chart": {
                    "type": "bar",
                    "title": "Loans by State",
                    "x_axis": "state",
                    "y_axis": "count"
                },
                "suggested_charts": [{"type": "pie", "title": "Distribution"}]
            }
        }


# =============================================
# MAIN RESPONSE SCHEMA
# =============================================

class ChatResponse(BaseModel):
    """
    Unified response from the chatbot router.
    
    The `backend` field indicates which sub-service handled the request.
    Frontend should use `backend` to determine how to render the response.
    """
    backend: BackendType = Field(
        ..., 
        description="Which backend service processed this request"
    )
    answer: str = Field(
        ..., 
        description="The main text response to display to the user"
    )
    session_id: str = Field(
        ..., 
        description="Session identifier. Store and send back in subsequent requests to maintain context"
    )
    tags: Optional[List[str]] = Field(
        None, 
        description="Topic tags (lf_assist only). Display as chips/badges below the answer"
    )
    data: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Query result data rows (viz_assist only). Render as table or chart"
    )
    sql_query: Optional[str] = Field(
        None, 
        description="Generated SQL query (viz_assist only). Show in collapsible section"
    )
    chart_analysis: Optional[ChartAnalysis] = Field(
        None, 
        description="Chart configuration (viz_assist only). Use to render charts"
    )
    record_count: Optional[int] = Field(
        None, 
        description="Number of data records returned (viz_assist only)"
    )
    error: Optional[str] = Field(
        None, 
        description="Error message if something went wrong. Display prominently if present"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "summary": "LF Assist Response",
                    "value": {
                        "backend": "lf_assist",
                        "answer": "To apply for a loan, you need to submit an application with your income documents...",
                        "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "tags": ["loan_application", "documentation"],
                        "data": None,
                        "sql_query": None,
                        "chart_analysis": None,
                        "record_count": None,
                        "error": None
                    }
                },
                {
                    "summary": "Visualization Response",
                    "value": {
                        "backend": "viz_assist",
                        "answer": "Query executed successfully. Retrieved 50 records.",
                        "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "tags": None,
                        "data": [{"state": "CA", "loan_count": 150}, {"state": "TX", "loan_count": 120}],
                        "sql_query": "SELECT state, COUNT(*) as loan_count FROM loans GROUP BY state",
                        "chart_analysis": {
                            "chartable": True,
                            "reasoning": "Categorical data suitable for bar chart",
                            "auto_chart": {"type": "bar", "title": "Loans by State", "x_axis": "state", "y_axis": "loan_count"}
                        },
                        "record_count": 50,
                        "error": None
                    }
                },
                {
                    "summary": "Scope Guard Deflection",
                    "value": {
                        "backend": "scope_guard",
                        "answer": "I'd love to help! My specialty is loan applications, policies, and data analysis. What can I help you with?",
                        "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "tags": None,
                        "data": None,
                        "sql_query": None,
                        "chart_analysis": None,
                        "record_count": None,
                        "error": None
                    }
                }
            ]
        }


# =============================================
# ERROR RESPONSE SCHEMAS
# =============================================

class ValidationErrorDetail(BaseModel):
    """Detail of a single validation error"""
    loc: List[str] = Field(..., description="Location of the error (field path)")
    msg: str = Field(..., description="Human-readable error message")
    type: str = Field(..., description="Error type identifier")


class ValidationErrorResponse(BaseModel):
    """Response returned when request validation fails (422)"""
    detail: List[ValidationErrorDetail] = Field(..., description="List of validation errors")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": [
                    {
                        "loc": ["body", "message"],
                        "msg": "field required",
                        "type": "value_error.missing"
                    }
                ]
            }
        }


class HTTPErrorResponse(BaseModel):
    """Response returned for HTTP errors (4xx, 5xx)"""
    detail: str = Field(..., description="Error description")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "File size exceeds the 5MB limit."
            }
        }


# =============================================
# UTILITY ENDPOINT SCHEMAS
# =============================================

class ClearSessionResponse(BaseModel):
    """Response for session clear endpoint"""
    message: str = Field(..., description="Status message")
    success: bool = Field(..., description="Whether the operation succeeded")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Session abc123 cleared",
                "success": True
            }
        }


class ServiceStatus(BaseModel):
    """Status of a single backend service"""
    lf_assist: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="LF Assist status")
    doc_assist: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Doc Assist status")
    db_assist: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="DB Assist status")
    viz_assist: Literal["healthy", "degraded", "initializing", "unhealthy"] = Field(..., description="Viz Assist status")
    scope_guard: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Scope Guard status")


class HealthCheckResponse(BaseModel):
    """Response for health check endpoint"""
    status: ServiceStatus = Field(..., description="Status of each backend service")
    message: str = Field(..., description="Overall health message")

    class Config:
        json_schema_extra = {
            "example": {
                "status": {
                    "lf_assist": "healthy",
                    "doc_assist": "healthy",
                    "db_assist": "healthy",
                    "viz_assist": "healthy",
                    "scope_guard": "healthy"
                },
                "message": "All backends integrated internally"
            }
        }


class RootResponse(BaseModel):
    """Response for root endpoint"""
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    backends: List[str] = Field(..., description="Available backend services")
    features: List[str] = Field(..., description="Enabled features")
    endpoints: Dict[str, str] = Field(..., description="Available endpoints mapping")

    class Config:
        json_schema_extra = {
            "example": {
                "service": "Unified Chatbot Router",
                "version": "3.1",
                "backends": ["lf_assist", "doc_assist", "db_assist", "viz_assist", "scope_guard"],
                "features": ["session_management", "scope_detection", "polite_deflection"],
                "endpoints": {
                    "unified": "/chat",
                    "lf_assist": "/lf-assist/chat"
                }
            }
        }

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
    
    gemini = get_gemini_client()
    
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Classification attempt {attempt + 1}/{max_retries + 1}")
            
            category = await gemini.generate_async(prompt)
            category = category.strip().lower()
            
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
            
            logger.warning(f"Unrecognized category: {category}")
            return "out_of_scope"
            
        except Exception as e:
            logger.error(f"Gemini classification error (attempt {attempt + 1}/{max_retries + 1}): {e}")
            
            if attempt == max_retries:
                logger.error("Max retries reached. Using fallback classification.")
                break
            
            delay = min(base_delay * (2 ** attempt), 10.0)
            jitter = random.uniform(0, 0.5)
            total_delay = delay + jitter
            
            logger.info(f"Retrying in {total_delay:.2f} seconds...")
            await asyncio.sleep(total_delay)
    
    logger.warning("Falling back to default classification")
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
    
    gemini = get_gemini_client()
    
    try:
        response = await gemini.generate_async(prompt)
        return response.strip()
    except Exception as e:
        logger.error(f"Error generating deflection: {e}")
        return (
            "I'd love to help you with that! My specialty is assisting with loan applications, "
            "policies, document reviews, account information, and data visualizations. "
            "What can I help you with regarding our lending services today?"
        )
    

def dump_model(obj):
    """Safely dump pydantic model (v1/v2 compatible)"""
    try:
        return obj.model_dump()
    except AttributeError:
        return obj.dict()

# --- Main Unified Chat Endpoint ---

@app.post(
    "/chat", 
    response_model=ChatResponse,
    responses={
        200: {
            "description": "Successful response from one of the backend services",
            "model": ChatResponse
        },
        400: {
            "description": "Bad request - Invalid file type or file too large",
            "model": HTTPErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_file": {
                            "summary": "Invalid file type",
                            "value": {"detail": "Invalid file type. Please upload a PDF."}
                        },
                        "file_too_large": {
                            "summary": "File too large",
                            "value": {"detail": "File size exceeds the 5MB limit."}
                        }
                    }
                }
            }
        },
        422: {
            "description": "Validation error - Missing or invalid fields",
            "model": ValidationErrorResponse
        },
        500: {
            "description": "Internal server error",
            "model": HTTPErrorResponse
        }
    },
    summary="Unified Chat Endpoint",
    description="""
    **Main unified chat endpoint** that intelligently routes queries to the appropriate backend service.
    
    ## Request Format
    Send as `multipart/form-data` with the following fields:
    - `message` (required): The user's natural language query
    - `session_id` (optional): Session ID from previous response. Omit for new conversations.
    - `file` (optional): PDF file for document Q&A. Max 5MB, 20 pages.
    
    ## Routing Logic
    The backend automatically classifies your query and routes to:
    - **lf_assist**: Company knowledge, policies, procedures
    - **doc_assist**: Questions about uploaded PDF documents
    - **db_assist**: Database lookups (loan status, account info)
    - **viz_assist**: Data visualization requests (charts, trends)
    - **scope_guard**: Out-of-scope queries (polite deflection)
    
    ## Frontend Integration
    1. Always display the `answer` field
    2. Store `session_id` and send it back in subsequent requests
    3. Check `backend` field to determine UI rendering:
       - `lf_assist`: Show `tags` as badges
       - `viz_assist`: Render `data` as table/chart using `chart_analysis`
       - Others: Display answer text only
    4. If `error` is present, show error state
    """
)
async def unified_chat(
    background_tasks: BackgroundTasks,
    message: str = Form(
        ..., 
        description="The user's natural language query",
        examples=["How do I apply for a loan?", "Show me a chart of loans by state"]
    ),
    session_id: Optional[str] = Form(
        default=None, 
        description="Session ID from previous response. Omit for new conversations."
    ),
    file: Optional[UploadFile] = File(
        default=None, 
        description="Optional PDF file for document Q&A. Max 5MB, 20 pages."
    ),
):
    
    # Generate or use existing session_id
    if not session_id:
        session_id = str(uuid4())
        logger.debug(f"New session: {session_id}")
    else:
        logger.debug(f"Continuing session: {session_id}")
    
    doc_uploaded = file is not None
    logger.info(f"Query: '{message}' | Doc: {doc_uploaded}")

    # Step 1: Classify the query
    category = await classify_query_with_gemini(message, doc_uploaded)
    logger.info(f"Category: {category}")
    
    # Step 2: Handle out-of-scope queries
    if category == "out_of_scope":
        logger.info("Out of scope - generating deflection response")
        answer = await generate_deflection_response(message)
        
        response_obj = ChatResponse(
            backend="scope_guard",
            answer=answer,
            session_id=session_id,
            tags=None
        )

        background_tasks.add_task(
            safe_log_to_redshift,
            session_id=session_id,
            chatbot="scope_guard",
            user_message=message,
            answer=answer,
            response_payload=dump_model(response_obj),
            is_error=False,
            error_message=None,
        )

        return response_obj

    
    # Step 3: Handle edge cases
    if category == "document q&a" and not doc_uploaded:
        logger.info("Document Q&A without file - fallback to LF Assist")
        category = "out_of_scope"

    # Step 4: Route to appropriate backend (direct function calls)
    answer = ""
    backend = ""
    tags = []
    data = None
    sql_query = None
    chart_analysis = None

    if category == "company knowledge":
        logger.info("Routing to LF Assist")
        result = await process_lf_chat(message, session_id)
        answer = result.answer
        tags = result.tags
        backend = "lf_assist"
        
    elif category == "document q&a":
        logger.info("Routing to Doc Assist")
        file_content = await file.read()
        answer = await process_pdf_question(message, file_content, file.filename)
        backend = "doc_assist"
        
    elif category == "database":
        logger.info("Routing to DB Assist")
        result = await process_db_query(message)
        answer = result["response"]
        backend = "db_assist"
        if not result.get("success", True):
             # If success is explicitly False, we can flag it, 
             # though usually the error message is in 'answer'
             pass
    
    elif category == "visualization":
        logger.info("Routing to Visualization Assist")
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
        logger.warning("Unknown category - fallback to LF Assist")
        result = await process_lf_chat(message, session_id)
        answer = result.answer
        tags = result.tags
        backend = "lf_assist"

    logger.info(f"Response from {backend}: {answer[:100]}...")

    response_obj = ChatResponse(
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

    background_tasks.add_task(
        safe_log_to_redshift,
        session_id=session_id,
        chatbot=backend,
        user_message=message,
        answer=answer,
        response_payload=dump_model(response_obj),
        is_error=False,
        error_message=None,
    )

    return response_obj


# --- Utility Endpoints ---

@app.post(
    "/chat/clear/{session_id}",
    response_model=ClearSessionResponse,
    responses={
        200: {
            "description": "Session cleared successfully",
            "model": ClearSessionResponse
        },
        500: {
            "description": "Failed to clear session",
            "model": ClearSessionResponse,
            "content": {
                "application/json": {
                    "example": {"message": "Error: Session not found", "success": False}
                }
            }
        }
    },
    summary="Clear Session History",
    description="""
    Clears the conversation history for a specific session.
    
    Use this endpoint when:
    - User wants to start a fresh conversation
    - Implementing a "New Chat" button
    - Cleaning up old sessions
    
    After clearing, subsequent requests with the same session_id will have no context.
    """
)
async def clear_session(
    session_id: str = Path(..., description="The session ID to clear")
) -> ClearSessionResponse:
    """Clear conversation history for LF Assist session"""
    try:
        clear_conversation(session_id)
        logger.info(f"Cleared session: {session_id}")
        return ClearSessionResponse(message=f"Session {session_id} cleared", success=True)
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        return ClearSessionResponse(message=f"Error: {str(e)}", success=False)

@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="""
    Check the health status of all backend services.
    
    Returns status for each backend:
    - `healthy`: Service is fully operational
    - `initializing`: Service is starting up (viz_assist only)
    - `degraded`: Service is partially working
    - `unhealthy`: Service is down
    
    Use for:
    - Load balancer health checks
    - Monitoring dashboards
    - Debugging connectivity issues
    """
)
async def health_check() -> HealthCheckResponse:
    """Check health of all backend services"""
    viz_service = VizChatbotService.get_instance()
    
    return HealthCheckResponse(
        status=ServiceStatus(
            lf_assist="healthy",
            doc_assist="healthy",
            db_assist="healthy",
            viz_assist="healthy" if viz_service.is_ready() else "initializing",
            scope_guard="healthy"
        ),
        message="All backends integrated internally"
    )

@app.get(
    "/",
    response_model=RootResponse,
    summary="API Information",
    description="Returns API metadata including version, available backends, and endpoint mappings."
)
def root() -> RootResponse:
    return RootResponse(
        service="Unified Chatbot Router",
        version="3.1",
        backends=["lf_assist", "doc_assist", "db_assist", "viz_assist", "scope_guard"],
        features=[
            "session_management",
            "scope_detection",
            "polite_deflection",
            "integrated_backends",
            "visualization_support"
        ],
        endpoints={
            "unified": "/chat",
            "lf_assist": "/lf-assist/chat",
            "doc_assist": "/doc-assist/ask",
            "db_assist": "/db-assist/chat",
            "viz_assist": "/viz-assist/chat"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("unified_api:app", host="0.0.0.0", port=8000, reload=True)
