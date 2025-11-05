from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import json
import asyncio
from langchain_aws import ChatBedrock
from .llm_model_bedrock import SQLQueryGenerator

class SQLAgentState(TypedDict):
    """State structure for the SQL agent workflow"""
    user_question: str
    schema_info: List[Dict[str, Any]]  # Overall database structure
    table_info: str                    # Specific table information (NEW)
    raw_sql_query: str
    cleaned_sql_query: str
    validation_result: Dict[str, Any]
    execution_result: str
    error_message: str
    current_step: str
    is_complete: bool

class SQLLangGraphAgentBedrock:
    def __init__(self, vector_store, embeddings, join_details, schema_info, query_runner=None):
        self.vector_store = vector_store
        self.embeddings = embeddings
        self.sql_generator = SQLQueryGenerator()
        self.join_details = join_details
        self.schema_info = schema_info 
        self.query_runner = query_runner
        
        # Initialize the LLM for any additional reasoning if needed
        self.llm = ChatBedrock(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            model_kwargs={"temperature": 0.1, "max_tokens": 2048}
        )
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Create the state graph
        workflow = StateGraph(SQLAgentState)
        
        # Add nodes
        workflow.add_node("schema_search", self._schema_search_node)
        workflow.add_node("sql_generation", self._sql_generation_node)
        workflow.add_node("query_validation", self._query_validation_node)
        workflow.add_node("query_execution", self._query_execution_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Set entry point
        workflow.set_entry_point("schema_search")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "schema_search",
            self._should_continue_after_schema,
            {
                "continue": "sql_generation",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "sql_generation",
            self._should_continue_after_generation,
            {
                "continue": "query_validation",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "query_validation",
            self._should_continue_after_validation,
            {
                "execute": "query_execution",
                "complete": END,
                "error": "error_handler"
            }
        )
        
        workflow.add_edge("query_execution", END)
        workflow.add_edge("error_handler", END)
        
        return workflow.compile()
    
    def _schema_search_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Search for relevant schema and table information"""
        try:
            
            # Search for schema information
            schema_results = self.vector_store.similarity_search_with_score(
                f"Which columns in the database are relevant to the following question: {state['user_question']}", 
                k=5
            )
            
            # Search for table-specific information
            table_results = self.vector_store.similarity_search_with_score(
                f"Table structure and metadata for: {state['user_question']}", 
                k=3
            )
            
            # Process schema information
            schema_info = []
            for res in schema_results:
                schema_info.append({
                    "content": res[0].page_content,
                    "score": float(res[1]),
                    "metadata": res[0].metadata if hasattr(res[0], 'metadata') else {}
                })
            
            # Process table information (separate from schema)
            table_info_list = []
            for res in table_results:
                table_info_list.append(res[0].page_content)
            
            # Join table info into a single string
            table_info_str = "\n".join(table_info_list)
            
            return {
                "schema_info": schema_info,
                "table_info": table_info_str,          # NEW field
                "current_step": "schema_search_complete",
                "error_message": ""
            }
            
        except Exception as e:
            return {
                "error_message": f"Schema search failed: {str(e)}",
                "current_step": "schema_search_failed"
            }

    
    def _sql_generation_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Generate SQL query based on schema information"""
        try:
            
            # Convert schema info to string format
            schema_content = [
                item["content"] + str(item["score"]) 
                for item in state["schema_info"]
            ]
            schema_info_str = "\n".join(schema_content)
            
            # Use schema_info for both parameters if table_info is not separately defined
            raw_query = self.sql_generator.generate_sql_query(
                user_request=state["user_question"],
                table_info=schema_info_str,          # Use schema info as table info
                schema_info=self.schema_info,         # Keep original schema info
                join_details=self.join_details,
                database_type="PostgreSQL",
                max_tokens=1000
            )
            
            return {
                "raw_sql_query": raw_query,
                "current_step": "sql_generation_complete",
                "error_message": ""
            }
            
        except Exception as e:
            return {
                "error_message": f"SQL generation failed: {str(e)}",
                "current_step": "sql_generation_failed"
            }

    
    def _query_validation_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Validate and clean the generated SQL query"""
        try:
            
            from ...tools.extract_query import extract_sql_query
            from ...db.safe_query_analyzer import _safe_sql
            
            # Extract clean SQL
            cleaned_query = extract_sql_query(state["raw_sql_query"], strip_comments=True)
            
            # Check safety
            safety_result = _safe_sql(cleaned_query)
            
            validation_result = {
                "is_safe": "unsafe" not in safety_result.lower(),
                "safety_message": safety_result,
                "has_syntax_errors": False  # You can add more validation here
            }
            
            return {
                "cleaned_sql_query": cleaned_query,
                "validation_result": validation_result,
                "current_step": "query_validation_complete",
                "error_message": ""
            }
            
        except Exception as e:
            return {
                "error_message": f"Query validation failed: {str(e)}",
                "current_step": "query_validation_failed"
            }
    
    def _query_execution_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Execute the validated SQL query"""
        try:
            
            if not self.query_runner:
                return {
                    "execution_result": "Query execution skipped - no query runner configured",
                    "current_step": "execution_skipped",
                    "is_complete": True
                }
            
            result = self.query_runner.run(state["cleaned_sql_query"])
            
            return {
                "execution_result": str(result),
                "current_step": "execution_complete",
                "is_complete": True,
                "error_message": ""
            }
            
        except Exception as e:
            return {
                "error_message": f"Query execution failed: {str(e)}",
                "current_step": "execution_failed",
                "is_complete": True
            }
    
    def _error_handler_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Handle errors and provide meaningful feedback"""
        print(f" Error occurred: {state.get('error_message', 'Unknown error')}")
        
        return {
            "current_step": "error_handled",
            "is_complete": True
        }
    
    # Conditional edge functions
    def _should_continue_after_schema(self, state: SQLAgentState) -> str:
        """Determine next step after schema search"""
        if state.get("error_message"):
            return "error"
        return "continue"
    
    def _should_continue_after_generation(self, state: SQLAgentState) -> str:
        """Determine next step after SQL generation"""
        if state.get("error_message"):
            return "error"
        return "continue"
    
    def _should_continue_after_validation(self, state: SQLAgentState) -> str:
        """Determine next step after validation"""
        if state.get("error_message"):
            return "error"
        
        validation_result = state.get("validation_result", {})
        
        # If query is safe and we have a query runner, execute it
        if validation_result.get("is_safe", False) and self.query_runner:
            return "execute"
        
        # Otherwise, complete the workflow
        return "complete"
    
    def process_query(self, user_question: str) -> Dict[str, Any]:
        """Process a user query through the complete workflow"""
        
        # Initialize state with the new table_info field
        initial_state = SQLAgentState(
            user_question=user_question,
            schema_info=[],
            table_info="",                    # NEW field initialization
            raw_sql_query="",
            cleaned_sql_query="",
            validation_result={},
            execution_result="",
            error_message="",
            current_step="initialized",
            is_complete=False
        )
        
        
        try:
            # Run the workflow
            final_state = self.workflow.invoke(initial_state)
            
            # Format the response
            return self._format_response(final_state)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Workflow execution failed: {str(e)}",
                "user_question": user_question
            }

    
    def _format_response(self, state: SQLAgentState) -> Dict[str, Any]:
        """Format the final response"""
        
        if state.get("error_message"):
            return {
                "success": False,
                "error": state["error_message"],
                "user_question": state["user_question"],
                "current_step": state.get("current_step", "unknown")
            }
        
        response = {
            "success": True,
            "user_question": state["user_question"],
            "schema_info": state.get("schema_info", []),
            "table_info": state.get("table_info", ""),        # NEW field in response
            "raw_sql_query": state.get("raw_sql_query", ""),
            "cleaned_sql_query": state.get("cleaned_sql_query", ""),
            "validation_result": state.get("validation_result", {}),
            "execution_result": state.get("execution_result", ""),
            "workflow_complete": state.get("is_complete", False)
        }
        
        return response
