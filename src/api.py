import sys
import os
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import StreamingResponse
import json

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_gemini import Chatbot

app = FastAPI()

# Initialize the chatbot
chatbot = Chatbot()

class ChatRequest(BaseModel):
    prompt: str

async def response_generator(prompt: str):
    """
    A generator function that yields the chatbot's response.
    """
    result = chatbot.get_response(prompt)
    
    if result and result.get('success'):
        response_data = result.get('execution_result', 'No execution result found.')
    elif result:
        response_data = result.get('error', 'An unknown error occurred.')
    else:
        response_data = "I'm sorry, something went wrong and I didn't get a result."

    # Stream the response
    if isinstance(response_data, str):
        yield response_data
    else:
        yield json.dumps(response_data)

# @app.post("/api/chat")
# async def chat(request: ChatRequest):
#     """
#     Endpoint to handle chat requests and stream the response.
#     """

#     return StreamingResponse(response_generator(request.prompt), media_type="text/event-stream")

from fastapi.responses import JSONResponse

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Endpoint to handle chat requests and return a standard JSON response.
    """
    result = await chatbot.get_response(request.prompt)

    if result and result.get('success'):
        response_data = result.get('execution_result', 'No execution result found.')
    elif result:
        response_data = result.get('error', 'An unknown error occurred.')
    else:
        response_data = "I'm sorry, something went wrong and I didn't get a result."

    return JSONResponse(content={"response": response_data})
