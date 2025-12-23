# app/utils/llm.py
from services import get_langchain_llm

# Get the singleton LangChain LLM instance
llm = get_langchain_llm()


def call_gemini(prompt):
    return llm.invoke(prompt).content
