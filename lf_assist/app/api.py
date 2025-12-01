# app/api.py
import re
from typing import Dict, List
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from lf_assist.app.query_tagger import tag_query
from lf_assist.app.retriever import get_relevant_chunks
from lf_assist.app.summarizer import summarize


# Global conversation storage (session_id -> list of messages)
conversation_store: Dict[str, List[BaseMessage]] = {}


TAG_PROMPT_PATH = r"lf_assist\prompts\query_tagger.txt"


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"  


class ChatResponse(BaseModel):
    query: str
    tags: list[str]
    answer: str
    session_id: str  


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
    
    # Keep only last 10 messages (20 turns) to prevent memory overflow
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
    """Format messages as dictionary for backward compatibility with existing functions"""
    return {
        "chat_history": messages,
        "history": format_chat_history(messages)
    }


def split_questions(query: str) -> list[str]:
    """
    Splits multi-question inputs into separate questions.
    Example: "Where can I see bank details? Can I update them?"
    """
    # Split on question marks or 'and' that appears to start a new sentence
    parts = re.split(r'\?\s*|\s+and\s+(?=[A-Z])', query.strip())
    return [p.strip() for p in parts if p.strip()]


def clear_conversation(session_id: str):
    """Clear conversation history for a specific session"""
    if session_id in conversation_store:
        del conversation_store[session_id]
        print(f"🗑️ Cleared conversation history for session: {session_id}")


def get_all_sessions() -> List[str]:
    """Get list of all active session IDs"""
    return list(conversation_store.keys())


@app.post("/chat")
def chat(request: ChatRequest):
    query = request.query
    session_id = request.session_id
    print(f"\n📥 Received query: {query} (session: {session_id})")

    # Get conversation history for this session
    messages = get_conversation_history(session_id)
    
    sub_questions = split_questions(query)
    print(f"🔍 Detected {len(sub_questions)} sub-question(s): {sub_questions}")

    all_chunks = []
    all_tags = []

    # Process each sub-question separately
    for q in sub_questions:
        try:
            tags = tag_query(q, TAG_PROMPT_PATH)
            print(f"🏷️ Tags for '{q}': {tags}")
        except Exception as e:
            print("⚠️ Error tagging query:", e)
            tags = []

        all_tags.extend(tags)

        try:
            # Pass formatted chat history instead of memory object
            chat_history_dict = format_chat_history_for_memory_dict(messages)
            chunks = get_relevant_chunks(q, tags, chat_history=chat_history_dict)
            print(f"📚 Retrieved {len(chunks)} chunks for '{q}'")
            for i, chunk in enumerate(chunks, 1):
                print(f"\n--- Chunk {i} ---\n{chunk}")
            all_chunks.extend(chunks)
        except Exception as e:
            print("❌ Retrieval Error:", e)

    # Deduplicate chunks
    all_chunks = list(set(all_chunks))
    formatted_chunks = [{"content": c} for c in all_chunks]

    # Show conversation history before summarization
    if messages:
        print("\n🧠 Current Conversation History:")
        for msg in messages:
            role = "User" if isinstance(msg, HumanMessage) else "Bot"
            print(f"{role}: {msg.content}")
    else:
        print("\n🧠 No conversation history yet.")

    # Summarization
    try:
        chat_history_dict = format_chat_history_for_memory_dict(messages)
        answer = summarize(query, formatted_chunks, chat_history=chat_history_dict)
    except Exception as e:
        print("Error summarizing:", e)
        answer = "⚠️ Failed to generate response."

    # Save to conversation history
    add_to_conversation(session_id, HumanMessage(content=query))
    add_to_conversation(session_id, AIMessage(content=answer))

    print(f"\n🤖 Final Answer: {answer}\n{'='*60}")
    return ChatResponse(
        query=query, 
        tags=list(set(all_tags)), 
        answer=answer,
        session_id=session_id
    )


@app.post("/chat/clear")
def clear_chat(session_id: str = "default"):
    """Clear conversation history for a session"""
    clear_conversation(session_id)
    return {"message": f"Conversation cleared for session: {session_id}"}


@app.get("/chat/sessions")
def list_sessions():
    """List all active session IDs"""
    return {"sessions": get_all_sessions(), "count": len(conversation_store)}


@app.get("/chat/history/{session_id}")
def get_history(session_id: str):
    """Get conversation history for a specific session"""
    messages = get_conversation_history(session_id)
    history = []
    for msg in messages:
        history.append({
            "role": "user" if isinstance(msg, HumanMessage) else "assistant",
            "content": msg.content
        })
    return {"session_id": session_id, "history": history, "message_count": len(messages)}
