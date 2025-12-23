import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from logger import logger

# Adjust imports to be relative to the 'src' directory
from db_assist.agents.gemini.sql_langgraph_agent_gemini import SQLLangGraphAgentGemini
from db_assist.db.vector_db_store import store_in_vector_db, get_vector_store
from db_assist.db.query_runner import RedshiftSQLTool

# Import schema and document information
from db.table_descriptions_semantic import documents, join_details, schema_info

# Load environment variables from .env file
load_dotenv()


class Chatbot:
    def __init__(self):
        
        # Initialize agent components once for efficiency
        self.vector_store = None
        self.query_runner = None
        self.gemini_agent = None
        self._init_agent_components()
    
    def _init_agent_components(self):
        """Initialize agent components once during chatbot creation"""
        logger.info("Initializing Gemini SQL Agent components...")
        
        # Load existing vector store
        try:
            self.vector_store = get_vector_store()
            if self.vector_store:
                logger.info("Existing vector store loaded successfully.")
            else:
                logger.warning("No existing vector store found.")
        except Exception as e:
            logger.error(f"Error loading existing vector store: {e}")
            self.vector_store = None
        
        # Initialize Query Runner
        try:
            self.query_runner = RedshiftSQLTool()
            logger.info("Redshift query runner initialized.")
        except Exception as e:
            logger.warning(f"Could not initialize Redshift query runner: {e}")
            self.query_runner = None
        
        # Initialize the Gemini Agent
        if self.vector_store:
            try:
                self.gemini_agent = SQLLangGraphAgentGemini(
                    vector_store=self.vector_store,
                    join_details=join_details,
                    schema_info=schema_info,
                    query_runner=self.query_runner
                )
                logger.info("Gemini SQL LangGraph Agent initialized successfully.")
            except Exception as e:
                logger.error(f"Error initializing Gemini agent: {e}")
                self.gemini_agent = None
        else:
            logger.error("Cannot initialize agent without vector store.")
            self.gemini_agent = None

    async def get_existing_vector_store(self):
        """
        Load the existing vector store collection without creating embeddings or re-embedding documents.
        Returns None if the collection does not exist.
        
        Note: This method is kept for backward compatibility, but vector_store is now loaded once in __init__.
        """
        if self.vector_store:
            return self.vector_store
        
        try:
            vector_store = get_vector_store()
            if vector_store:
                logger.info("Existing vector store loaded successfully.")
                self.vector_store = vector_store
            else:
                logger.warning("No existing vector store found.")
            return vector_store
        except Exception as e:
            logger.error(f"Error loading existing vector store: {e}")
            return None

    async def get_response(self, user_question: str, thread_id: str = "default"):
        """
        Processes the user's question as a database query.
        
        Args:
            user_question: The user's question
            thread_id: Unique identifier for the conversation thread (e.g., user_id or session_id)
        """
        logger.debug(f"Processing query for thread: {thread_id}")
        
        # Check if agent is initialized
        if not self.gemini_agent:
            return {"error": "SQL Agent not initialized. Please check if vector store exists."}
        
        if not self.vector_store:
            return {"error": "No existing vector store found. Please create the vector store first."}

        # Process the user question with thread_id
        logger.info(f"Processing user question: '{user_question}'")

        try:
            # The agent now handles chat history internally via LangGraph's checkpointer
            result = self.gemini_agent.process_query(user_question, thread_id=thread_id)

            # Log the final result
            logger.debug(f"Agent result - Success: {result.get('success')}")
            if result.get('success'):
                logger.debug(f"Cleaned SQL Query: {result.get('cleaned_sql_query')}")
            else:
                logger.error(f"Agent error: {result.get('error')}")
            return result

        except Exception as e:
            logger.error(f"An error occurred during query processing: {e}")
            return {"error": f"An error occurred during query processing: {e}"}
    
    def reinitialize_agent(self):
        """Reinitialize the agent (useful if vector store is updated)"""
        logger.info("Reinitializing agent components...")
        self._init_agent_components()
    
    def get_agent_status(self):
        """Get the initialization status of agent components"""
        return {
            "vector_store_loaded": self.vector_store is not None,
            "query_runner_loaded": self.query_runner is not None,
            "agent_initialized": self.gemini_agent is not None
        }
