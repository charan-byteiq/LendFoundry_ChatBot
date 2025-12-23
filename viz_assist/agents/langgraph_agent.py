import os
import json
import logging
from typing import TypedDict, Annotated, List, Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from services import get_langchain_llm

# Assumed import from your project structure
from .llm_model_gemini import SQLQueryGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLAgentState(TypedDict):
    """State structure for the SQL agent workflow"""
    user_question: str
    messages: Annotated[List[BaseMessage], add_messages]
    schema_info: List[Dict[str, Any]]
    raw_sql_query: str
    cleaned_sql_query: str
    validation_result: Dict[str, Any]
    execution_result: str
    execution_data_json: str
    chart_analysis: Dict[str, Any]
    error_message: str
    current_step: str
    is_complete: bool
    retry_count: int

class SQLLangGraphAgentGemini:
    def __init__(self, vector_store, join_details, schema_info, query_runner=None):
        self.vector_store = vector_store
        self.sql_generator = SQLQueryGenerator()
        self.join_details = join_details
        self.schema_info = schema_info 
        self.query_runner = query_runner
        self._current_thread_id = "default"  # Store thread_id for logging
        
        self.db_structure = """
        DATABASE STRUCTURE (Schema -> Tables):
        Schema : fl_lms
        contains tables : accrual_balances, loan_onboarding, loan_filters

        Schema : public
        contains tables : los_borrower_application, los_offer, los_address
        
        Schema : cdp
        contains tables : customerdataproductfinal
        """
        
        # Use centralized LangChain LLM service
        self.llm = get_langchain_llm()
        
        # Add checkpointer for persistence
        self.checkpointer = MemorySaver()
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(SQLAgentState)
        
        # Add nodes
        workflow.add_node("rewrite_question", self._rewrite_question_node)
        workflow.add_node("schema_search", self._schema_search_node)
        workflow.add_node("sql_generation", self._sql_generation_node)
        workflow.add_node("query_validation", self._query_validation_node)
        workflow.add_node("query_execution", self._query_execution_node)
        workflow.add_node("chart_analysis", self._chart_analysis_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Set entry point
        workflow.set_entry_point("rewrite_question")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "rewrite_question",
            self._should_continue_after_rewrite,
            {"continue": "schema_search", "error": "error_handler"}
        )

        workflow.add_conditional_edges(
            "schema_search",
            self._should_continue_after_schema,
            {"continue": "sql_generation", "error": "error_handler"}
        )
        
        workflow.add_conditional_edges(
            "sql_generation",
            self._should_continue_after_generation,
            {"continue": "query_validation", "error": "error_handler"}
        )
        
        workflow.add_conditional_edges(
            "query_validation",
            self._should_continue_after_validation,
            {"execute": "query_execution", "complete": END, "error": "error_handler"}
        )
        
        workflow.add_conditional_edges(
            "query_execution",
            self._should_retry_after_execution,
            {"retry": "sql_generation", "continue": "chart_analysis", "error": "error_handler"}
        )
        
        # End after chart analysis or error
        workflow.add_edge("chart_analysis", END)
        workflow.add_edge("error_handler", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _rewrite_question_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Rewrite the user's question to be more specific based on chat history"""
        try:
            if len(state['messages']) <= 1:
                return {
                    "user_question": state['user_question'],
                    "current_step": "question_rewriting_skipped"
                }

            # Format chat history
            chat_history_messages = []
            for msg in state['messages'][:-1]:
                if isinstance(msg, HumanMessage):
                    chat_history_messages.append(f"User: {msg.content}")
                elif isinstance(msg, AIMessage):
                    chat_history_messages.append(f"Assistant: {msg.content}")
            
            chat_history_text = "\n".join(chat_history_messages)

            rewrite_prompt = ChatPromptTemplate.from_messages([
                ("system", "Given the chat history and a follow-up question, rewrite the follow-up question to be a standalone question."),
                ("human", "Chat History:\n{chat_history}\n\nFollow-up Question:\n{question}\n\nStandalone Question:")
            ])
            
            rewriter_chain = rewrite_prompt | self.llm
            
            rewritten_question_message = rewriter_chain.invoke({
                "chat_history": chat_history_text,
                "question": state['user_question']
            })
            
            rewritten_question = rewritten_question_message.content.strip()
            
            return {
                "user_question": rewritten_question,
                "current_step": "question_rewriting_complete"
            }
            
        except Exception as e:
            return {
                "error_message": f"Question rewriting failed: {str(e)}",
                "current_step": "question_rewriting_failed"
            }

    def _schema_search_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Search ONLY for relevant schema information"""
        try:
            full_query = f"User Question: {state['user_question']}"

            # Search only for schema information
            schema_results = self.vector_store.similarity_search_with_score(
                f"Which columns in the database are relevant to the following question: {full_query}", 
                k=5
            )
            
            logger.info(f"Schema search results: {schema_results}")
            
            schema_info = []
            for res in schema_results:
                schema_info.append({
                    "content": res[0].page_content,
                    "score": float(res[1]),
                    "metadata": res[0].metadata if hasattr(res[0], 'metadata') else {}
                })
            
            return {
                "schema_info": schema_info,
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
            # Format chat history
            chat_history_messages = []
            for msg in state['messages'][:-1]:
                if isinstance(msg, HumanMessage):
                    chat_history_messages.append(f"User: {msg.content}")
                elif isinstance(msg, AIMessage):
                    chat_history_messages.append(f"Assistant: {msg.content}")
            
            chat_history_text = "\n".join(chat_history_messages)
            
            full_query = f"{chat_history_text}\n\nUser Question: {state['user_question']}" if chat_history_text else f"User Question: {state['user_question']}"

            # Get detailed column definitions
            detailed_columns = [item["content"] for item in state["schema_info"]]
            detailed_columns_str = "\n".join(detailed_columns)
            
            # Combine the Global Map + Detailed Columns
            combined_schema_context = f"""
            {self.db_structure}

            DETAILED COLUMN DEFINITIONS (Relevant to this query):
            {detailed_columns_str}
            """
            
            # Generate SQL
            raw_query = self.sql_generator.generate_sql_query(
                user_request=full_query,
                schema_info=combined_schema_context,
                join_details=self.join_details,
                database_type="Redshift"
            )
            
            if raw_query is None:
                raise ValueError("SQL Generator returned None")

            logger.debug(f"Generated SQL Query: {raw_query}")
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
            if not state["raw_sql_query"]:
                return {
                    "error_message": "SQL generation returned no query.",
                    "current_step": "query_validation_failed"
                }

            from tools.extract_query import extract_sql_query
            from db.safe_query_analyzer import _safe_sql
            
            cleaned_query = extract_sql_query(state["raw_sql_query"], strip_comments=True)
            safety_result = _safe_sql(cleaned_query)
            
            validation_result = {
                "is_safe": "unsafe" not in safety_result.lower(),
                "safety_message": safety_result,
                "has_syntax_errors": False
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
        """Execute the validated SQL query and LOG to database"""
        try:
            logger.info(f"Executing SQL Query: {state['cleaned_sql_query']}")
            if not self.query_runner:
                return {
                    "execution_result": "Query execution skipped - no query runner configured",
                    "execution_data_json": json.dumps({"error": "No query runner configured"}),
                    "current_step": "execution_skipped",
                    "is_complete": True
                }
            
            # Execute the query
            result = self.query_runner.run(state["cleaned_sql_query"])
            
            execution_data_json = ""
            execution_result = ""
            row_count = 0
            
            if result is not None:
                try:
                    # Handle Pandas DataFrame
                    if hasattr(result, 'to_dict'):
                        records = result.to_dict(orient='records')
                        execution_data_json = json.dumps(records, default=str)
                        row_count = len(result)
                        execution_result = f"Query returned {row_count} rows"
                    # Handle list of dicts
                    elif isinstance(result, list):
                        execution_data_json = json.dumps(result, default=str)
                        row_count = len(result)
                        execution_result = f"Query returned {row_count} rows"
                    # Handle single dict
                    elif isinstance(result, dict):
                        execution_data_json = json.dumps([result], default=str)
                        row_count = 1
                        execution_result = "Query returned 1 row"
                    else:
                        raise ValueError("Query runner must return DataFrame, list[dict], or dict")
                except Exception as json_error:
                    logger.error(f"JSON conversion error: {json_error}")
                    execution_data_json = json.dumps({"error": f"Could not convert to JSON: {str(json_error)}"})
                    execution_result = f"Error: {str(json_error)}"
            else:
                execution_data_json = json.dumps([])
                execution_result = "No data returned"
            
            # LOG SUCCESSFUL QUERY EXECUTION TO DATABASE
            self.query_runner.log_query(
                user_question=state["user_question"],
                generated_sql=state["cleaned_sql_query"],
                thread_id=self._current_thread_id,
                execution_status="success",
                row_count=row_count
            )
            
            return {
                "execution_result": execution_result,
                "execution_data_json": execution_data_json,
                "current_step": "execution_complete",
                "is_complete": False,  # Continue to chart analysis
                "error_message": ""
            }
            
        except Exception as e:
            # LOG FAILED QUERY EXECUTION TO DATABASE
            if self.query_runner and state.get("cleaned_sql_query"):
                self.query_runner.log_query(
                    user_question=state["user_question"],
                    generated_sql=state["cleaned_sql_query"],
                    thread_id=self._current_thread_id,
                    execution_status=f"failed: {str(e)[:200]}",
                    row_count=0
                )
            
            return {
                "error_message": f"Query execution failed: {str(e)}",
                "current_step": "execution_failed",
                "retry_count": state.get("retry_count", 0) + 1
            }

    def _chart_analysis_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Analyze data for chart visualization using LLM"""
        try:
            data_result = state.get("execution_data_json", "")
            question = state.get("user_question", "")
            
            # Validate JSON structure
            try:
                parsed_data = json.loads(data_result)
            except Exception:
                parsed_data = []
            
            # Check if data is structured and non-empty
            if not isinstance(parsed_data, list) or len(parsed_data) == 0:
                return {
                    "chart_analysis": {
                        "chartable": False,
                        "reasoning": "Result is not structured tabular data or is empty",
                        "suggested_charts": [],
                        "auto_chart": {"type": "", "title": "", "reason": "No valid data"}
                    },
                    "messages": [AIMessage(content=f"Query executed successfully.\n\nResult: No data returned.")],
                    "current_step": "chart_analysis_complete",
                    "is_complete": True
                }
            
            # Truncate data for token limit
            data_sample = str(data_result)[:2000] if len(str(data_result)) > 2000 else str(data_result)
            
            chart_analysis_prompt = f"""You are a data visualization expert. Analyze if this data can be visualized.

                                        User Question:
                                        {question}

                                        Data Sample:
                                        {data_sample}

                                        Respond with ONLY valid JSON in this exact structure (no markdown, no code blocks):
                                        {{{{
                                        "chartable": true,
                                        "reasoning": "Explanation",
                                        "suggested_charts": [
                                            {{{{
                                            "type": "bar",
                                            "title": "Chart Title",
                                            "x_axis": "column_name",
                                            "y_axis": "column_name",
                                            "reason": "Why this fits",
                                            "confidence": 0.85
                                            }}}}
                                        ],
                                        "auto_chart": {{{{
                                            "type": "bar",
                                            "title": "Best Chart",
                                            "x_axis": "column_name",
                                            "y_axis": "column_name",
                                            "reason": "Why best"
                                        }}}}
                                        }}}}"""

            # Invoke LLM
            chart_response_message = self.llm.invoke([HumanMessage(content=chart_analysis_prompt)])
            chart_response = chart_response_message.content.strip().replace('``````', '')
            
            try:
                chart_analysis = json.loads(chart_response)
            except (json.JSONDecodeError, ValueError):
                chart_analysis = {
                    'chartable': False,
                    'suggested_charts': [],
                    'auto_chart': {'type': '', 'title': '', 'reason': 'Parsing failed'},
                    'reasoning': 'LLM response parsing failed.'
                }

            response_msg_text = (
                f"Query executed successfully.\n\n"
                f"SQL Query:\n``````\n\n"
                f"Chart Analysis:\n{chart_analysis.get('reasoning', '')}\n"
                f"Chartable: {chart_analysis.get('chartable', False)}"
            )

            return {
                "chart_analysis": chart_analysis,
                "messages": [AIMessage(content=response_msg_text)],
                "current_step": "chart_analysis_complete",
                "is_complete": True,
                "error_message": ""
            }
            
        except Exception as e:
            return {
                "chart_analysis": {'chartable': False, 'reasoning': f"Error: {e}"},
                "messages": [AIMessage(content="Query executed, but chart analysis failed.")],
                "current_step": "chart_analysis_failed",
                "is_complete": True,
                "error_message": ""
            }

    def _error_handler_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Handle errors"""
        error_msg = state.get('error_message', 'Unknown error')
        return {
            "messages": [AIMessage(content=f"Error: {error_msg}")],
            "execution_result": error_msg,
            "execution_data_json": json.dumps({"error": error_msg}),
            "current_step": "error_handled",
            "is_complete": True
        }
    
    # Conditional logic
    def _should_continue_after_rewrite(self, state: SQLAgentState) -> str:
        return "error" if state.get("error_message") else "continue"

    def _should_continue_after_schema(self, state: SQLAgentState) -> str:
        return "error" if state.get("error_message") else "continue"
    
    def _should_continue_after_generation(self, state: SQLAgentState) -> str:
        return "error" if state.get("error_message") else "continue"
    
    def _should_continue_after_validation(self, state: SQLAgentState) -> str:
        if state.get("error_message"): return "error"
        if state.get("validation_result", {}).get("is_safe", False) and self.query_runner:
            return "execute"
        return "complete"
    
    def _should_retry_after_execution(self, state: SQLAgentState) -> str:
        if state.get("error_message"):
            if state.get("retry_count", 0) < 3: return "retry"
            else: return "error"
        return "continue"
    
    def process_query(self, user_question: str, thread_id: str = "default") -> Dict[str, Any]:
        """Process a user query through the complete workflow"""
        
        #  Store thread_id for logging purposes
        self._current_thread_id = thread_id
        
        initial_state = SQLAgentState(
            user_question=user_question,
            messages=[HumanMessage(content=user_question)],
            schema_info=[],
            raw_sql_query="",
            cleaned_sql_query="",
            validation_result={},
            execution_result="",
            execution_data_json="",
            chart_analysis={},
            error_message="",
            current_step="initialized",
            is_complete=False,
            retry_count=0
        )
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            final_state = self.workflow.invoke(initial_state, config)
            return self._format_response(final_state)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _format_response(self, state: SQLAgentState) -> Dict[str, Any]:
        """Format final response"""
        if state.get("error_message"):
            return {
                "success": False,
                "error": state["error_message"],
                "execution_data_json": state.get("execution_data_json", json.dumps({"error": state["error_message"]}))
            }
        
        return {
            "success": True,
            "user_question": state["user_question"],
            "cleaned_sql_query": state.get("cleaned_sql_query", ""),
            "execution_data_json": state.get("execution_data_json", ""),
            "chart_analysis": state.get("chart_analysis", {}),
            "workflow_complete": state.get("is_complete", False)
        }
