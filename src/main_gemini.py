import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_classic.memory import ConversationBufferMemory
import google.generativeai as genai


# Adjust imports to be relative to the 'src' directory
from src.agents.gemini.sql_langgraph_agent_gemini import SQLLangGraphAgentGemini
from src.db.vector_db_store import store_in_vector_db, get_vector_store
from src.db.query_runner import RedshiftSQLTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI


# Import schema and document information
from db.table_descriptions_semantic import documents, join_details, schema_info


# Load environment variables from .env file
load_dotenv()


# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)


class Chatbot:
    def __init__(self):
        self.memory = ConversationBufferMemory()

    async def get_existing_vector_store(self):
        """
        Load the existing vector store collection without creating embeddings or re-embedding documents.
        Returns None if the collection does not exist.
        """
        try:
            vector_store = get_vector_store()  # Loads existing store directly
            if vector_store:
                print("Existing vector store loaded successfully.")
            else:
                print("No existing vector store found.")
            return vector_store
        except Exception as e:
            print(f"Error loading existing vector store: {e}")
            return None

    async def get_response(self, user_question):
        """
        Processes the user's question as a database query.
        """
        print("Initializing Gemini SQL Agent...")

        # Load existing vector store without re-embedding
        vector_store = await self.get_existing_vector_store()
        if not vector_store:
            return {"error": "No existing vector store found. Please create the vector store first."}

        # Initialize Query Runner (optional)
        try:
            query_runner = RedshiftSQLTool()
            print("Redshift query runner initialized.")
        except Exception as e:
            print(f"Could not initialize Redshift query runner: {e}")
            query_runner = None

        # Initialize the Gemini Agent
        try:
            gemini_agent = SQLLangGraphAgentGemini(
                vector_store=vector_store,
                join_details=join_details,
                schema_info=schema_info,
                query_runner=query_runner,
                memory=self.memory
            )
            print("Gemini SQL LangGraph Agent initialized successfully.")
        except Exception as e:
            print(f"Error initializing Gemini agent: {e}")
            return {"error": f"Error initializing Gemini agent: {e}"}

        # Process the user question
        print(f"\nProcessing user question: '{user_question}'")

        try:
            result = gemini_agent.process_query(user_question)

            # Print the final result
            print("\n--- Agent Final Result ---")
            print(f"Success: {result.get('success')}")
            if result.get('success'):
                print(f"User Question: {result.get('user_question')}")
                print(f"Cleaned SQL Query: {result.get('cleaned_sql_query')}")
                print(f"Execution Result: {result.get('execution_result', 'N/A')}")
            else:
                print(f"Error: {result.get('error')}")
            print("--------------------------")
            return result

        except Exception as e:
            print(f"An error occurred during query processing: {e}")
            return {"error": f"An error occurred during query processing: {e}"}


