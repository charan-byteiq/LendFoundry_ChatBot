import os
import sys
import logging
import json
from typing import Optional, Dict, Any, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai

try:
    from viz_assist.agents.langgraph_agent import SQLLangGraphAgentGemini
    from viz_assist.db.vector_db_store import get_vector_store
    from viz_assist.db.query_runner import RedshiftSQLTool
    from viz_assist.db.table_descriptions_semantic import join_details, schema_info
except ImportError as e:
    print(f"Critical Import Error: {e}")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
# Note: google-genai Client auto-uses GOOGLE_API_KEY from environment

router = APIRouter(prefix="/viz-assist", tags=["Visualization Assist"])

class ChatRequest(BaseModel):
    question: str = Field(..., description="The user's natural language query")
    thread_id: str = Field(default="default", description="Session ID for conversation history")

class ChartConfig(BaseModel):
    type: str
    title: str
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    reason: Optional[str] = None

class ChartAnalysis(BaseModel):
    chartable: bool
    reasoning: Optional[str] = None
    auto_chart: Optional[ChartConfig] = None
    suggested_charts: Optional[List[Dict[str, Any]]] = None

class ChatResponse(BaseModel):
    sql_query: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    chart_analysis: Optional[ChartAnalysis] = None
    error: Optional[str] = None
    record_count: int = 0

class VizChatbotService:
    """Visualization Chatbot Service - Singleton instance"""
    _instance = None
    
    def __init__(self):
        self.vector_store = None
        self.query_runner = None
        self.gemini_agent = None
        self._initialized = False
    
    @classmethod
    def get_instance(cls):
        """Get or create singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def initialize(self):
        """Initialize agent components - called during app startup"""
        if self._initialized:
            logger.info("Viz service already initialized")
            return
        
        logger.info("Initializing Visualization Gemini SQL Agent components...")
        
        # Load existing vector store
        try:
            self.vector_store = get_vector_store()
            if self.vector_store:
                logger.info("✓ Viz: Existing vector store loaded successfully.")
            else:
                logger.warning("⚠ Viz: Warning: No existing vector store found.")
        except Exception as e:
            logger.error(f"✗ Viz: Error loading vector store: {e}")
            self.vector_store = None
        
        # Initialize Query Runner
        try:
            self.query_runner = RedshiftSQLTool()
            logger.info("✓ Viz: Redshift query runner initialized.")
        except Exception as e:
            logger.error(f"⚠ Viz: Could not initialize Redshift query runner: {e}")
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
                logger.info("✓ Viz: Gemini SQL LangGraph Agent initialized successfully.")
                self._initialized = True
            except Exception as e:
                logger.error(f"✗ Viz: Error initializing Gemini agent: {e}")
                self.gemini_agent = None
        else:
            logger.error("✗ Viz: Cannot initialize agent without vector store.")
            self.gemini_agent = None
    
    async def get_response(self, user_question: str, thread_id: str = "default") -> Dict[str, Any]:
        """Processes the user's visualization question"""
        
        if not self._initialized or not self.gemini_agent:
            return {"error": "SQL Agent not initialized. Server error or missing vector store.", "success": False}
        
        if not self.vector_store:
            return {"error": "No existing vector store found.", "success": False}

        logger.info(f"Viz: Processing query for thread: {thread_id} | Q: {user_question}")

        try:
            result = self.gemini_agent.process_query(user_question, thread_id=thread_id)
            return result
        except Exception as e:
            logger.exception("Viz: Error occurred during query processing")
            return {"error": str(e), "success": False}
    
    def is_ready(self) -> bool:
        """Check if service is ready"""
        return self._initialized and self.gemini_agent is not None

# Core function for direct calling from unified API
async def process_viz_query(question: str, thread_id: str = "default") -> ChatResponse:
    """
    Core visualization processing logic - can be called directly from unified API
    """
    service = VizChatbotService.get_instance()
    
    if not service.is_ready():
        return ChatResponse(
            sql_query="",
            data=[],
            record_count=0,
            chart_analysis=ChartAnalysis(chartable=False, reasoning="Service not initialized"),
            error="Visualization agent is not fully initialized. Check server logs."
        )
    
    # Get raw response from agent
    raw_result = await service.get_response(question, thread_id)
    
    # Handle Errors from the agent
    if raw_result.get("error") or not raw_result.get("success", True):
        return ChatResponse(
            sql_query=raw_result.get("cleaned_sql_query", ""),
            data=[],
            record_count=0,
            chart_analysis=ChartAnalysis(chartable=False, reasoning="Error occurred"),
            error=raw_result.get("error", "Unknown error occurred processing query")
        )
    
    # Parse JSON data string to Python Object
    data_content = []
    execution_data_str = raw_result.get("execution_data_json", "[]")
    try:
        parsed = json.loads(execution_data_str)
        if isinstance(parsed, list):
            data_content = parsed
        elif isinstance(parsed, dict):
            if "error" in parsed:
                logger.warning(f"Query returned error: {parsed.get('error')}")
                data_content = []
            else:
                data_content = [parsed]
        else:
            data_content = []
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse execution_data_json: {e}")
        data_content = []
    
    # Map raw result to Pydantic Response
    response = ChatResponse(
        sql_query=raw_result.get("cleaned_sql_query", ""),
        data=data_content,
        record_count=len(data_content),
        chart_analysis=raw_result.get("chart_analysis", ChartAnalysis(chartable=False, reasoning="No analysis available"))
    )
    
    return response

# --- Router Endpoints ---

@router.get("/health")
async def health_check():
    """Check the health of the visualization agent components"""
    service = VizChatbotService.get_instance()
    
    status_report = {
        "vector_store": service.vector_store is not None,
        "query_runner": service.query_runner is not None,
        "agent_ready": service.gemini_agent is not None,
        "initialized": service._initialized
    }
    
    if not service.is_ready():
        return JSONResponse(status_code=503, content=status_report)
    
    return status_report

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Visualization chat endpoint.
    Receives a natural language question and returns SQL data + chart config.
    """
    return await process_viz_query(request.question, request.thread_id)
