from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from .llm_model_gemini import SQLQueryGenerator
from langchain_core.prompts import ChatPromptTemplate
import os


class SQLAgentState(TypedDict):
    """State structure for the SQL agent workflow"""
    user_question: str
    messages: Annotated[List[BaseMessage], add_messages]
    retrieved_schema_chunks: List[Dict[str, Any]]
    raw_sql_query: str
    cleaned_sql_query: str
    validation_result: Dict[str, Any]
    execution_result: str
    natural_language_response: str
    error_message: str
    current_step: str
    is_complete: bool
    retry_count: int


class SQLLangGraphAgentGemini:
    def __init__(self, vector_store, join_details, schema_info, query_runner=None):
        self.vector_store = vector_store
        self.sql_generator = SQLQueryGenerator(model_name="gemini-2.5-flash")
        self.join_details = join_details
        self.db_structure = schema_info
        self.query_runner = query_runner
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.1,
            max_output_tokens=2048,
            convert_system_message_to_human=True,
        )
        
        self.checkpointer = MemorySaver()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(SQLAgentState)
        
        workflow.add_node("rewrite_question", self._rewrite_question_node)
        workflow.add_node("schema_search", self._schema_search_node)
        workflow.add_node("sql_generation", self._sql_generation_node)
        workflow.add_node("query_validation", self._query_validation_node)
        workflow.add_node("query_execution", self._query_execution_node)
        workflow.add_node("natural_language_generation", self._natural_language_generation_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        workflow.set_entry_point("rewrite_question")
        
        workflow.add_conditional_edges(
            "rewrite_question",
            self._should_continue_after_rewrite,
            {
                "continue": "schema_search",
                "error": "error_handler"
            }
        )

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
        
        workflow.add_conditional_edges(
            "query_execution",
            self._should_retry_after_execution,
            {
                "retry": "sql_generation",
                "continue": "natural_language_generation",
                "error": "error_handler"
            }
        )
        
        workflow.add_edge("natural_language_generation", END)
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

            chat_history_messages = []
            for msg in state['messages'][:-1]:
                if isinstance(msg, HumanMessage):
                    chat_history_messages.append(f"User: {msg.content}")
                elif isinstance(msg, AIMessage):
                    chat_history_messages.append(f"Assistant: {msg.content}")
            
            chat_history_text = "\n".join(chat_history_messages)

            rewrite_prompt = ChatPromptTemplate.from_messages([
                ("system", "[LendFoundry Question Rewriting] Given the following chat history and a follow-up question, rewrite the follow-up question to be a standalone question."),
                ("human", "<chat_history>\n{chat_history}\n</chat_history>\n\n<follow_up_question>\n{question}\n</follow_up_question>\n\n<standalone_question>")
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
        """Search for relevant schema information"""
        try:
            full_query = state["user_question"]

            schema_results = self.vector_store.similarity_search_with_score(full_query, k=5)
            
            retrieved = []
            for doc, score in schema_results:
                retrieved.append({
                    "content": doc.page_content,
                    "score": float(score),
                    "metadata": getattr(doc, "metadata", {}) or {}
                })
            
            return {
                "retrieved_schema_chunks": retrieved,
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
            chat_history_messages = []
            for msg in state['messages'][:-1]:
                if isinstance(msg, HumanMessage):
                    chat_history_messages.append(f"User: {msg.content}")
                elif isinstance(msg, AIMessage):
                    chat_history_messages.append(f"Assistant: {msg.content}")
            
            chat_history_text = "\n".join(chat_history_messages)
            
            full_user_request = (
                f"{chat_history_text}\n\nUser Question: {state['user_question']}"
                if chat_history_text else state["user_question"]
            )

            retrieved_context = "\n".join(
                c["content"] for c in state.get("retrieved_schema_chunks", []) if c.get("content")
            ).strip()

            db_structure_text = str(self.db_structure or "")

            schema_info_for_llm = f"""
[RETRIEVED_SCHEMA_CHUNKS]
{retrieved_context}

[DATABASE_STRUCTURE_NOTE]
The database is organized into schemas and tables as follows:
{db_structure_text}
""".strip()
            
            raw_query = self.sql_generator.generate_sql_query(
                user_request=full_user_request,
                schema_info=schema_info_for_llm,
                join_details=str(self.join_details or ""),
                database_type="Redshift",
            )
            
            return {
                "raw_sql_query": raw_query or "",
                "current_step": "sql_generation_complete",
                "error_message": "" if raw_query else "SQL generation returned no query.",
            }
            
        except Exception as e:
            return {
                "error_message": f"SQL generation failed: {str(e)}",
                "current_step": "sql_generation_failed",
            }
    
    def _query_validation_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Validate and clean the generated SQL query"""
        try:
            if not state["raw_sql_query"]:
                return {
                    "error_message": "SQL generation returned no query.",
                    "current_step": "query_validation_failed"
                }

            from ...tools.extract_query import extract_sql_query
            from ...db.safe_query_analyzer import _safe_sql
            
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
        """Execute the validated SQL query and log it to database"""
        try:
            # Log the query to database BEFORE execution
            if self.query_runner and state.get("cleaned_sql_query"):
                thread_id = getattr(self, '_current_thread_id', 'default')
                self.query_runner.log_query(
                    user_question=state["user_question"],
                    generated_sql=state["cleaned_sql_query"],
                    thread_id=thread_id,
                    execution_status="pending"
                )
            
            if not self.query_runner:
                return {
                    "execution_result": "Query execution skipped - no query runner configured",
                    "current_step": "execution_skipped",
                    "is_complete": True
                }
            
            result = self.query_runner.run(state["cleaned_sql_query"])
            
            # Update log with success status (optional - requires UPDATE query)
            # For now, we just log once with "success" status after execution succeeds
            
            return {
                "execution_result": str(result),
                "current_step": "execution_complete",
                "is_complete": False,
                "error_message": ""
            }
            
        except Exception as e:
            # Log the failure
            if self.query_runner and state.get("cleaned_sql_query"):
                thread_id = getattr(self, '_current_thread_id', 'default')
                self.query_runner.log_query(
                    user_question=state["user_question"],
                    generated_sql=state["cleaned_sql_query"],
                    thread_id=thread_id,
                    execution_status=f"failed: {str(e)[:200]}"
                )
            
            return {
                "error_message": f"Query execution failed: {str(e)}",
                "current_step": "execution_failed",
                "retry_count": state.get("retry_count", 0) + 1
            }


    def _natural_language_generation_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Generate a natural language response based on the SQL query result."""
        try:
            if state.get("error_message") and "Query execution failed" in state.get("error_message", ""):
                error_msg = state["error_message"]
                return {
                    "messages": [AIMessage(content=error_msg)],
                    "execution_result": error_msg,
                    "natural_language_response": error_msg,
                    "current_step": "error_forwarded",
                    "is_complete": True
                }
            
            nl_prompt = ChatPromptTemplate.from_messages([
                ("system", "[LendFoundry NL Generation] You are a chatbot which is getting the response from a LLM. A user asked the following question:"),
                ("human", "<user_question>\n{question}\n</user_question>\n\nYou have already executed a SQL query and retrieved the following data:\n<data>\n{data}\n</data>\n\nPlease provide a clear and concise answer to the user's question based on the data.\nAnswer in a natural, conversational tone.\nDo not expose the columns which were used in the query.\nDo not give any sensitive information.")
            ])
            
            nl_chain = nl_prompt | self.llm
            
            nl_response_message = nl_chain.invoke({
                "question": state["user_question"],
                "data": state.get("execution_result", "")
            })

            natural_language_response = (nl_response_message.content or "").strip()
            
            return {
                "messages": [AIMessage(content=natural_language_response)],
                "natural_language_response": natural_language_response,
                "execution_result": state.get("execution_result", ""),
                "current_step": "natural_language_generation_complete",
                "is_complete": True
            }
            
        except Exception as e:
            error_msg = f"Natural language generation failed: {str(e)}"
            return {
                "messages": [AIMessage(content=error_msg)],
                "error_message": error_msg,
                "natural_language_response": error_msg,
                "current_step": "natural_language_generation_failed",
                "is_complete": True
            }
    
    def _error_handler_node(self, state: SQLAgentState) -> Dict[str, Any]:
        """Handle errors and provide meaningful feedback"""
        error_msg = state.get('error_message', 'Unknown error')
        print(f"Error occurred: {error_msg}")
        
        return {
            "messages": [AIMessage(content=error_msg)],
            "execution_result": error_msg,
            "natural_language_response": error_msg,
            "current_step": "error_handled",
            "is_complete": True
        }
    
    def _should_continue_after_rewrite(self, state: SQLAgentState) -> str:
        """Determine next step after question rewriting"""
        if state.get("error_message"):
            return "error"
        return "continue"

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
        
        if validation_result.get("is_safe", False) and self.query_runner:
            return "execute"
        
        return "complete"
    
    def _should_retry_after_execution(self, state: SQLAgentState) -> str:
        """Determine whether to retry SQL generation after a failed execution."""
        if state.get("error_message"):
            if state.get("retry_count", 0) < 3:
                return "retry"
            else:
                return "error"
        return "continue"
    
    def process_query(self, user_question: str, thread_id: str = "default") -> Dict[str, Any]:
        """Process a user query through the complete workflow
        
        Args:
            user_question: The user's question
            thread_id: Unique identifier for the conversation thread (e.g., user_id or session_id)
        """
        
        # Store thread_id for logging purposes
        self._current_thread_id = thread_id
        
        initial_state = SQLAgentState(
            user_question=user_question,
            messages=[HumanMessage(content=user_question)],
            retrieved_schema_chunks=[],
            raw_sql_query="",
            cleaned_sql_query="",
            validation_result={},
            execution_result="",
            natural_language_response="",
            error_message="",
            current_step="initialized",
            is_complete=False,
            retry_count=0
        )
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            final_state = self.workflow.invoke(initial_state, config)
            response = self._format_response(final_state)
            return response
            
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
            "retrieved_schema_chunks": state.get("retrieved_schema_chunks", []),
            "raw_sql_query": state.get("raw_sql_query", ""),
            "cleaned_sql_query": state.get("cleaned_sql_query", ""),
            "validation_result": state.get("validation_result", {}),
            "execution_result": state.get("execution_result", ""),
            "natural_language_response": state.get("natural_language_response", ""),
            "workflow_complete": state.get("is_complete", False)
        }
        
        return response
