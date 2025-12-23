# app/api.py
import re
from typing import Dict, List, Optional
from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from lf_assist.app.query_tagger import tag_query
from lf_assist.app.retriever import get_relevant_chunks
from lf_assist.app.summarizer import summarize
from logger import logger

# Global conversation storage (session_id -> list of messages)
conversation_store: Dict[str, List[BaseMessage]] = {}

TAG_PROMPT_PATH = r"lf_assist\prompts\query_tagger.txt"

# Create router instead of app
router = APIRouter(prefix="/lf-assist", tags=["LF Assist"])


# =============================================
# REQUEST/RESPONSE SCHEMAS
# =============================================

class ChatRequest(BaseModel):
    """Request body for LF Assist chat endpoint"""
    query: str = Field(
        ..., 
        description="The user's natural language question about company policies or procedures",
        min_length=1,
        max_length=2000
    )
    session_id: str = Field(
        default="default",
        description="Session ID for maintaining conversation context. Use same ID for follow-up questions."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "How do I apply for a business loan?",
                "session_id": "user_123_session_456"
            }
        }


class ChatResponse(BaseModel):
    """Response from LF Assist chat endpoint"""
    query: str = Field(..., description="Echo of the original query")
    tags: List[str] = Field(..., description="Topic tags extracted from the query (e.g., 'loan_application', 'interest_rates')")
    answer: str = Field(..., description="The generated answer based on company knowledge base")
    session_id: str = Field(..., description="Session ID for follow-up requests")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "How do I apply for a business loan?",
                "tags": ["loan_application", "business_loan", "process"],
                "answer": "To apply for a business loan, you need to submit the following documents...",
                "session_id": "user_123_session_456"
            }
        }


class ClearChatResponse(BaseModel):
    """Response for chat clear endpoint"""
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {"message": "Conversation cleared for session: user_123"}
        }


class SessionListResponse(BaseModel):
    """Response listing active sessions"""
    sessions: List[str] = Field(..., description="List of active session IDs")
    count: int = Field(..., description="Total number of active sessions")

    class Config:
        json_schema_extra = {
            "example": {
                "sessions": ["user_123", "user_456", "default"],
                "count": 3
            }
        }


class HistoryMessage(BaseModel):
    """A single message in conversation history"""
    role: str = Field(..., description="Message sender: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class HistoryResponse(BaseModel):
    """Response containing conversation history"""
    session_id: str = Field(..., description="The session ID")
    history: List[HistoryMessage] = Field(..., description="List of messages in conversation order")
    message_count: int = Field(..., description="Total number of messages in history")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "user_123",
                "history": [
                    {"role": "user", "content": "How do I apply for a loan?"},
                    {"role": "assistant", "content": "To apply for a loan, you need to..."}
                ],
                "message_count": 2
            }
        }

def get_conversation_history(session_id: str) -> List[BaseMessage]:
    """Get conversation history for a specific session"""
    if session_id not in conversation_store:
        conversation_store[session_id] = []
    return conversation_store[session_id]

def add_to_conversation(session_id: str, message: BaseMessage):
    """Add a message to conversation history"""
    if session_id not in conversation_store:
        conversation_store[session_id] = []
    conversation_store[session_id].append(message)
    
    if len(conversation_store[session_id]) > 20:
        conversation_store[session_id] = conversation_store[session_id][-20:]

def format_chat_history(messages: List[BaseMessage]) -> str:
    """Format message history as string for prompts"""
    formatted = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            formatted.append(f"Assistant: {msg.content}")
    return "\n".join(formatted)

def format_chat_history_for_memory_dict(messages: List[BaseMessage]) -> dict:
    """Format messages as dictionary for backward compatibility"""
    return {
        "chat_history": messages,
        "history": format_chat_history(messages)
    }

def split_questions(query: str) -> list[str]:
    """Splits multi-question inputs into separate questions."""
    parts = re.split(r'\?\s*|\s+and\s+(?=[A-Z])', query.strip())
    return [p.strip() for p in parts if p.strip()]

def clear_conversation(session_id: str):
    """Clear conversation history for a specific session"""
    if session_id in conversation_store:
        del conversation_store[session_id]
        logger.info(f"Cleared conversation history for session: {session_id}")

def get_all_sessions() -> List[str]:
    """Get list of all active session IDs"""
    return list(conversation_store.keys())

# Core logic extracted as callable function
async def process_lf_chat(query: str, session_id: str = "default") -> ChatResponse:
    """
    Core LF Assist logic - can be called directly from unified API
    """
    logger.info(f"Received query: {query} (session: {session_id})")
    
    messages = get_conversation_history(session_id)
    sub_questions = split_questions(query)
    logger.debug(f"Detected {len(sub_questions)} sub-question(s): {sub_questions}")
    
    all_chunks = []
    all_tags = []
    
    for q in sub_questions:
        try:
            tags = tag_query(q, TAG_PROMPT_PATH)
            logger.debug(f"Tags for '{q}': {tags}")
        except Exception as e:
            logger.error(f"Error tagging query: {e}")
            tags = []
        
        all_tags.extend(tags)
        
        try:
            chat_history_dict = format_chat_history_for_memory_dict(messages)
            chunks = get_relevant_chunks(q, tags, chat_history=chat_history_dict)
            logger.debug(f"Retrieved {len(chunks)} chunks for '{q}'")
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error(f"Retrieval Error: {e}")
    
    all_chunks = list(set(all_chunks))
    formatted_chunks = [{"content": c} for c in all_chunks]
    
    # Removed verbose conversation history logging
    
    try:
        chat_history_dict = format_chat_history_for_memory_dict(messages)
        answer = summarize(query, formatted_chunks, chat_history=chat_history_dict)
    except Exception as e:
        logger.error(f"Error summarizing: {e}")
        answer = "⚠️ Failed to generate response."
    
    add_to_conversation(session_id, HumanMessage(content=query))
    add_to_conversation(session_id, AIMessage(content=answer))
    
    logger.info(f"Final Answer: {answer[:100]}...")
    return ChatResponse(
        query=query,
        tags=list(set(all_tags)),
        answer=answer,
        session_id=session_id
    )

# Router endpoints
@router.post(
    "/chat", 
    response_model=ChatResponse,
    summary="Company Knowledge Chat",
    description="""
    Ask questions about company policies, lending procedures, loan products, and services.
    
    The system will:
    1. Tag the query with relevant topics
    2. Retrieve relevant information from the knowledge base
    3. Generate a contextual answer
    4. Maintain conversation history for follow-up questions
    
    **Examples:**
    - "How do I apply for a loan?"
    - "What interest rates do you offer?"
    - "What documents are required for a business loan?"
    """
)
async def chat(request: ChatRequest) -> ChatResponse:
    return await process_lf_chat(request.query, request.session_id)


@router.post(
    "/chat/clear",
    response_model=ClearChatResponse,
    summary="Clear Session",
    description="Clear conversation history for a specific session. Use for 'New Chat' functionality."
)
async def clear_chat(
    session_id: str = Query(default="default", description="Session ID to clear")
) -> ClearChatResponse:
    """Clear conversation history for a session"""
    clear_conversation(session_id)
    return ClearChatResponse(message=f"Conversation cleared for session: {session_id}")


@router.get(
    "/chat/sessions",
    response_model=SessionListResponse,
    summary="List Active Sessions",
    description="Get a list of all active session IDs. Useful for admin/debug purposes."
)
async def list_sessions() -> SessionListResponse:
    """List all active session IDs"""
    return SessionListResponse(sessions=get_all_sessions(), count=len(conversation_store))


@router.get(
    "/chat/history/{session_id}",
    response_model=HistoryResponse,
    summary="Get Conversation History",
    description="Retrieve the full conversation history for a specific session."
)
async def get_history(
    session_id: str = Path(..., description="The session ID to get history for")
) -> HistoryResponse:
    """Get conversation history for a specific session"""
    messages = get_conversation_history(session_id)
    history = []
    for msg in messages:
        history.append(HistoryMessage(
            role="user" if isinstance(msg, HumanMessage) else "assistant",
            content=msg.content
        ))
    return HistoryResponse(session_id=session_id, history=history, message_count=len(messages))
