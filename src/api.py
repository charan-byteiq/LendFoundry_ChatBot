import sys
import os
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import uuid

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_gemini import Chatbot

app = FastAPI()

# Initialize the chatbot
chatbot = Chatbot()


class ChatRequest(BaseModel):
    prompt: str
    thread_id: str = None  # Optional: unique identifier for user/session
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Show me total loan amount",
                "thread_id": "user_123_session_456"
            }
        }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Endpoint to handle chat requests and return a standard JSON response.
    
    Args:
        request.prompt: User's question
        request.thread_id: Optional unique identifier for the conversation thread.
                          If not provided, generates a new one (no history).
    """
    # Generate thread_id if not provided (new conversation)
    thread_id = request.thread_id or str(uuid.uuid4())
    
    # Process the query with thread_id for conversation persistence
    result = await chatbot.get_response(request.prompt, thread_id=thread_id)
    
    if result and result.get('success'):
        response_data = result.get('execution_result', 'No execution result found.')
    elif result:
        response_data = result.get('error', 'An unknown error occurred.')
    else:
        response_data = "I'm sorry, something went wrong and I didn't get a result."
    
    return JSONResponse(content={
        "response": response_data,
        "thread_id": thread_id,  # Return thread_id so client can reuse it
        "success": result.get('success', False)
    })


@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify agent status"""
    status = chatbot.get_agent_status()
    return JSONResponse(content={
        "status": "healthy" if all(status.values()) else "degraded",
        "components": status
    })
