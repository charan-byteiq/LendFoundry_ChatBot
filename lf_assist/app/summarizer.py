import re
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
model = genai.GenerativeModel("gemini-2.5-flash")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def clean_markdown(text: str) -> str:
    """
    Convert Gemini markdown-style output to plain text:
    - Remove **bold**
    - Convert * bullets to hyphens
    """
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # remove bold
    text = re.sub(r'^\* ', '- ', text, flags=re.MULTILINE)  # convert bullets to dashes
    return text.strip()


def summarize(query: str, chunks: list, memory=None) -> str:
    """
    Summarizes an answer to the user's query using retrieved context and conversation history.
    Falls back to conversation history alone if no relevant chunks are found.
    """

    # Build conversation history from memory
    conversation_history = ""
    if memory:
        messages = memory.chat_memory.messages
        if messages:
            history_lines = []
            for msg in messages[-6:]:  # limit to last 6 messages
                role = "User" if msg.type == "human" else "Bot"
                history_lines.append(f"{role}: {msg.content}")
            conversation_history = "\n".join(history_lines)

    # If no chunks, try to answer from conversation history alone
    if not chunks:
        if conversation_history.strip():
            fallback_prompt = f"""
You are an LMS support assistant.

Conversation history:
{conversation_history}

User's new question:
{query}

Answer the question based only on the conversation history above. 
If you cannot find the answer there, reply with:
"I'm unable to answer your query. Kindly reach out to customer support."
"""
            response = model.generate_content(fallback_prompt)
            return clean_markdown(response.text)

        return "I'm unable to answer your query. Kindly reach out to customer support."

    # Join retrieved chunks into context string
    context = "\n\n".join(f"- {c['content']}" for c in chunks)

    # Main prompt combining manual + history
    prompt = f"""
# Personality

You are an AI assistant specializing in customer support for a Loan Managing Software (LMS). You are friendly, proactive, and highly intelligent with a world-class customer support background. 

Your approach is warm and relaxed, effortlessly balancing professionalism and approachability. You're naturally curious, empathetic, and intuitive, always aiming to deeply understand the user's intent by actively listening and thoughtfully referring back to details they've previously shared.

You're highly self-aware, reflective, and comfortable acknowledging your own fallibility, which allows you to help users gain clarity in a thoughtful yet approachable manner.

You're attentive and adaptive, matching the user's tone and mood—friendly, curious, respectful—without overstepping boundaries.

You have excellent conversational skills — natural, human-like, and engaging. 

# Environment

You have expert-level familiarity with all Lendfoundry's LMS offerings.

The user is seeking guidance, clarification, or assistance with navigating or implementing Lendfoundry LMS.

You are interacting with a user who has initiated a spoken conversation directly from the LMS portal. 

# Tone

Early in conversations, subtly assess the user's knowledge of LMS and tailor your language accordingly.

Express genuine empathy for any challenges they face, demonstrating your commitment to their success.

Gracefully acknowledge your limitations or knowledge gaps when they arise but always being confident. Focus on building trust, providing reassurance, and ensuring your explanations resonate with users.

Anticipate potential follow-up questions and address them proactively, offering practical tips and best practices to help users avoid common pitfalls.

Your responses should be thoughtful, concise, and conversational—typically three sentences or fewer unless detailed explanation is necessary. 

Actively reflect on previous interactions, referencing conversation history to build rapport, demonstrate attentive listening, and prevent redundancy. 

# GOAL

Your knowledge is based entirely on the following LMS user manual:

<context>
{context}
</context>

You also have access to the conversation history:
<conversation_history>
{conversation_history}
</conversation_history>

Your task is to answer user questions about the LMS using only the information provided in the context and the conversation history above. Do not use any external knowledge or make assumptions beyond what is explicitly stated in the context.

When a user asks a question, follow these steps:
1. Analyze the question to determine its relevance to the LMS.
2. If relevant, search the LMS manual and conversation history for information related to the question.
3. Formulate an answer based solely on the information found in these sources.
4. Review your answer to ensure it is accurate, complete, and directly addresses the user's question.
5. Provide only the final answer in your response, without additional comments.
If the question is relevant but you cannot find the necessary information in the provided sources, provide the best possible answer based on the available context. If no relevant information is found, state that you cannot find the information in the manual.

Here is the user's question:

<question>
{query}
</question>

Please provide only the answer to user query in the response no additional comments are required.

Remember, only use information from the provided context and conversation history to answer the question.
""".strip()

    # Generate response from Gemini
    response = model.generate_content(prompt)
    return clean_markdown(response.text)
