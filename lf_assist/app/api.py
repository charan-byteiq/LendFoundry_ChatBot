# app/api.py
import re
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from lf_assist.app.query_tagger import tag_query
from lf_assist.app.retriever import get_relevant_chunks
from lf_assist.app.summarizer import summarize
from langchain_classic.memory import ConversationBufferMemory

# Global memory (conversation buffer)
memory = ConversationBufferMemory(
    return_messages=True,
    memory_key="chat_history",
    input_key="query",
    k=3
)

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

class ChatResponse(BaseModel):
    query: str
    tags: list[str]
    answer: str


def split_questions(query: str) -> list[str]:
    """
    Splits multi-question inputs into separate questions.
    Example: "Where can I see bank details? Can I update them?"
    """
    # Split on question marks or 'and' that appears to start a new sentence
    parts = re.split(r'\?\s*|\s+and\s+(?=[A-Z])', query.strip())
    return [p.strip() for p in parts if p.strip()]


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    query = request.query
    print(f"\n📥 Received query: {query}")

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
            chunks = get_relevant_chunks(q, tags, memory=memory)
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
    if memory.chat_memory.messages:
        print("\n🧠 Current Conversation History:")
        for msg in memory.chat_memory.messages:
            role = "User" if msg.type == "human" else "Bot"
            print(f"{role}: {msg.content}")
    else:
        print("\n🧠 No conversation history yet.")

    # Summarization
    try:
        answer = summarize(query, formatted_chunks, memory=memory)
    except Exception as e:
        print("Error summarizing:", e)
        answer = "⚠️ Failed to generate response."

    # Save to memory
    memory.chat_memory.add_user_message(query)
    memory.chat_memory.add_ai_message(answer)

    print(f"\n🤖 Final Answer: {answer}\n{'='*60}")
    return ChatResponse(query=query, tags=list(set(all_tags)), answer=answer)
