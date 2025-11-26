from langchain_classic.memory import ConversationBufferMemory
from dotenv import load_dotenv
from lf_assist.app.retriever import get_relevant_chunks
from lf_assist.app.summarizer import summarize
from lf_assist.app.query_tagger import tag_query

load_dotenv()

TAG_PROMPT_PATH = "prompts/query_tagger.txt"

# Initialize memory
memory = ConversationBufferMemory(
    return_messages=True,
    memory_key="chat_history",
    input_key="input"
)

print("\n💬 LMS Chatbot (type 'exit' to quit)")
print("👉 You can ask follow-up questions in the same session.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() == "exit":
        print("🔚 Ending session.")
        break
    if not user_input:
        continue

    try:
        tags = tag_query(user_input, TAG_PROMPT_PATH)
    except Exception as e:
        print("⚠️ Error tagging query:", e)
        tags = []

    try:
        retrieved_chunks = get_relevant_chunks(user_input, tags)
    except Exception as e:
        print("❌ Retrieval Error:", e)
        retrieved_chunks = []

    # Filter and format chunks
    formatted_chunks = [{"content": c} for c in retrieved_chunks if c]

    # 🔍 Print the retrieved chunks
    if formatted_chunks:
        print("\n📚 Retrieved Chunks:")
        for idx, chunk in enumerate(formatted_chunks, 1):
            print(f"\n--- Chunk {idx} ---\n{chunk['content']}")
        print("\n")  # Extra spacing
    else:
        print("⚠️ No relevant chunks retrieved.\n")

    try:
        if formatted_chunks:
            response = summarize(user_input, formatted_chunks, memory=memory)
            memory.chat_memory.add_user_message(user_input)
            memory.chat_memory.add_ai_message(response)
        else:
            response = "⚠️ No relevant information found in the manual for your query."
    except Exception as e:
        response = "⚠️ Failed to generate response."
        print("Gemini Error:", e)

    print(f"Bot: {response}\n")
