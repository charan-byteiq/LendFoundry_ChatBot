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

try:
    from viz_assist.agents.langgraph_agent import SQLLangGraphAgentGemini
    from viz_assist.db.vector_db_store import get_vector_store
    from viz_assist.db.query_runner import RedshiftSQLTool
    from viz_assist.db.table_descriptions_semantic import join_details, schema_info
except ImportError as e:
    import sys
    sys.stderr.write(f"Critical Import Error: {e}\n")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
# Note: google-genai Client auto-uses GOOGLE_API_KEY from environment

router = APIRouter(prefix="/viz-assist", tags=["Visualization Assist"])


# =============================================
# REQUEST/RESPONSE SCHEMAS
# =============================================

class ChatRequest(BaseModel):
    """Request body for visualization chat endpoint"""
    question: str = Field(
        ..., 
        description="Natural language query requesting data visualization",
        min_length=1,
        max_length=2000
    )
    thread_id: str = Field(
        default="default", 
        description="Session ID for conversation history"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Show me a bar chart of loan amounts by state",
                "thread_id": "user_123_session_456"
            }
        }

class ChartConfig(BaseModel):
    """Configuration for rendering a chart"""
    type: str = Field(..., description="Chart type: 'bar', 'line', 'pie', 'scatter', 'area'")
    title: str = Field(..., description="Title to display on the chart")
    x_axis: Optional[str] = Field(None, description="Data key for X-axis")
    y_axis: Optional[str] = Field(None, description="Data key for Y-axis")
    reason: Optional[str] = Field(None, description="Why this chart type was recommended")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "bar",
                "title": "Loan Distribution by State",
                "x_axis": "state",
                "y_axis": "loan_count",
                "reason": "Bar chart is ideal for comparing categorical data"
            }
        }


class ChartAnalysis(BaseModel):
    """Analysis result determining if and how data should be visualized"""
    chartable: bool = Field(..., description="Whether the data is suitable for chart visualization")
    reasoning: Optional[str] = Field(None, description="Explanation of the chartability decision")
    auto_chart: Optional[ChartConfig] = Field(None, description="Recommended chart configuration")
    suggested_charts: Optional[List[Dict[str, Any]]] = Field(None, description="Alternative chart options")

    class Config:
        json_schema_extra = {
            "example": {
                "chartable": True,
                "reasoning": "Data has categorical X values and numeric Y values, suitable for visualization",
                "auto_chart": {
                    "type": "bar",
                    "title": "Loans by State",
                    "x_axis": "state",
                    "y_axis": "count"
                },
                "suggested_charts": [{"type": "pie", "title": "State Distribution"}]
            }
        }

class ChatResponse(BaseModel):
    """Response from visualization endpoint containing query results and chart config"""
    sql_query: Optional[str] = Field(None, description="The generated SQL query (for debugging/transparency)")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="Query result data rows to visualize")
    chart_analysis: Optional[ChartAnalysis] = Field(None, description="Chart configuration and analysis")
    error: Optional[str] = Field(None, description="Error message if query failed")
    record_count: int = Field(default=0, description="Number of data records returned")

    class Config:
        json_schema_extra = {
            "example": {
                "sql_query": "SELECT state, COUNT(*) as loan_count FROM loans GROUP BY state",
                "data": [
                    {"state": "CA", "loan_count": 150},
                    {"state": "TX", "loan_count": 120},
                    {"state": "NY", "loan_count": 100}
                ],
                "chart_analysis": {
                    "chartable": True,
                    "reasoning": "Categorical data suitable for bar chart",
                    "auto_chart": {
                        "type": "bar",
                        "title": "Loans by State",
                        "x_axis": "state",
                        "y_axis": "loan_count"
                    }
                },
                "error": None,
                "record_count": 3
            }
        }


class VizHealthResponse(BaseModel):
    """Health check response for visualization service"""
    vector_store: bool = Field(..., description="Vector store connection status")
    query_runner: bool = Field(..., description="Database query runner status")
    agent_ready: bool = Field(..., description="SQL agent initialization status")
    initialized: bool = Field(..., description="Overall service initialization status")

    class Config:
        json_schema_extra = {
            "example": {
                "vector_store": True,
                "query_runner": True,
                "agent_ready": True,
                "initialized": True
            }
        }

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

@router.get(
    "/health",
    response_model=VizHealthResponse,
    responses={
        200: {"description": "Service is healthy", "model": VizHealthResponse},
        503: {"description": "Service is not ready", "model": VizHealthResponse}
    },
    summary="Health Check",
    description="Check the health status of visualization service components."
)
async def health_check() -> VizHealthResponse:
    """Check the health of the visualization agent components"""
    service = VizChatbotService.get_instance()
    
    response = VizHealthResponse(
        vector_store=service.vector_store is not None,
        query_runner=service.query_runner is not None,
        agent_ready=service.gemini_agent is not None,
        initialized=service._initialized
    )
    
    if not service.is_ready():
        return JSONResponse(status_code=503, content=response.dict())
    
    return response


@router.post(
    "/chat", 
    response_model=ChatResponse,
    summary="Visualization Query",
    description="""
    Execute a natural language query and receive data with chart configuration.
    
    The system will:
    1. Understand your visualization request
    2. Generate and execute appropriate SQL
    3. Analyze the data for chart suitability
    4. Return data + recommended chart configuration
    
    **Visualization Keywords:**
    - "chart", "graph", "plot", "visualize"
    - "trend", "compare", "distribution"
    - "show me", "display"
    
    **Examples:**
    - "Show me a bar chart of loan amounts by state"
    - "Plot the monthly loan trend for 2024"
    - "Visualize the distribution of interest rates"
    - "Compare loan products by average amount"
    
    **Frontend Integration:**
    1. Check `chart_analysis.chartable` to see if data can be charted
    2. Use `chart_analysis.auto_chart` for recommended chart config
    3. Use `data` array to render the chart or table
    4. Optionally display `sql_query` in a collapsible section
    """
)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Visualization chat endpoint - returns SQL data + chart config"""
    return await process_viz_query(request.question, request.thread_id)
