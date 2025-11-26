# app/utils/llm.py
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import GOOGLE_API_KEY

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0,
    max_output_tokens=20000,
)

def call_gemini(prompt):
    return llm.invoke(prompt).content
