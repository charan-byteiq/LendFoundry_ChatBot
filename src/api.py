import sys
import os
from fastapi import APIRouter
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_gemini import Chatbot


router = APIRouter(prefix="/db-assist", tags=["DB Assist"])

chatbot = Chatbot()


# =============================================
# REQUEST/RESPONSE SCHEMAS
# =============================================

class ChatRequest(BaseModel):
    """Request body for DB Assist chat endpoint"""
    prompt: str = Field(
        ...,
        description="The user's natural language database query",
        min_length=1,
        max_length=2000
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Thread ID for conversation context. If not provided, a new one will be generated."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Show me total loan amount by state",
                "thread_id": "user_123_session_456"
            }
        }


class ChatResponse(BaseModel):
    """Response from DB Assist chat endpoint"""
    response: str = Field(..., description="The natural language response explaining the query result")
    thread_id: str = Field(..., description="Thread ID for follow-up queries")
    success: bool = Field(..., description="Whether the query executed successfully")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "The total loan amount is $1,500,000 across 150 active loans.",
                "thread_id": "user_123_session_456",
                "success": True
            }
        }


class HealthStatus(BaseModel):
    """Status of individual components"""
    vector_store: bool = Field(..., description="Vector store connection status")
    query_runner: bool = Field(..., description="Database query runner status")
    agent: bool = Field(..., description="SQL agent initialization status")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall health status: 'healthy' or 'degraded'")
    components: HealthStatus = Field(..., description="Status of individual components")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "components": {
                    "vector_store": True,
                    "query_runner": True,
                    "agent": True
                }
            }
        }

async def process_db_query(prompt: str, thread_id: str = None) -> dict:
    """
    Core DB Assist logic - can be called directly from unified API
    """
    # Generate thread_id if not provided
    thread_id = thread_id or str(uuid.uuid4())
    
    # Process the query
    result = await chatbot.get_response(prompt, thread_id=thread_id)
    
    if result and result.get('success'):
        response_data = result.get('natural_language_response', 'No execution result found.')
    elif result:
        response_data = result.get('error', 'An unknown error occurred.')
    else:
        response_data = "I'm sorry, something went wrong and I didn't get a result."
    
    return {
        "response": response_data,
        "thread_id": thread_id,
        "success": result.get('success', False)
    }

# Router endpoints
@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Database Query Chat",
    description="""
    Execute natural language queries against the loan database.
    
    The system will:
    1. Understand your natural language question
    2. Generate and execute appropriate SQL
    3. Return results in natural language
    
    **Examples:**
    - "What is the status of loan #12345?"
    - "How many active loans are there?"
    - "Show me the total loan amount"
    - "List loans from California"
    
    **Note:** For visualization requests (charts, graphs), use the `/viz-assist/chat` endpoint.
    """
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Endpoint to handle chat requests and return a standard JSON response.
    """
    result = await process_db_query(request.prompt, request.thread_id)
    return ChatResponse(
        response=result["response"],
        thread_id=result["thread_id"],
        success=result["success"]
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the health status of DB Assist components including vector store, query runner, and SQL agent."
)
async def health_check() -> HealthResponse:
    """Health check endpoint to verify agent status"""
    status = chatbot.get_agent_status()
    return HealthResponse(
        status="healthy" if all(status.values()) else "degraded",
        components=HealthStatus(
            vector_store=status.get("vector_store", False),
            query_runner=status.get("query_runner", False),
            agent=status.get("agent", False)
        )
    )
