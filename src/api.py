import sys
import os
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import uuid

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_gemini import Chatbot

# Create router instead of app
router = APIRouter(prefix="/db-assist", tags=["DB Assist"])

# Initialize the chatbot
chatbot = Chatbot()

class ChatRequest(BaseModel):
    prompt: str
    thread_id: str = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Show me total loan amount",
                "thread_id": "user_123_session_456"
            }
        }

# Core logic extracted as callable function
async def process_db_query(prompt: str, thread_id: str = None) -> dict:
    """
    Core DB Assist logic - can be called directly from unified API
    """
    # Generate thread_id if not provided
    thread_id = thread_id or str(uuid.uuid4())
    
    # Process the query
    result = await chatbot.get_response(prompt, thread_id=thread_id)
    
    if result and result.get('success'):
        response_data = result.get('execution_result', 'No execution result found.')
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
@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Endpoint to handle chat requests and return a standard JSON response.
    """
    result = await process_db_query(request.prompt, request.thread_id)
    return JSONResponse(content=result)

@router.get("/health")
async def health_check():
    """Health check endpoint to verify agent status"""
    status = chatbot.get_agent_status()
    return JSONResponse(content={
        "status": "healthy" if all(status.values()) else "degraded",
        "components": status
    })
