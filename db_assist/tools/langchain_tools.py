from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List, Dict, Any
from langchain.agents import initialize_agent, AgentType
from langchain_core.agents import AgentAction, AgentFinish
from langchain_aws import ChatBedrock
from db.safe_query_analyzer import _safe_sql
import json

class SchemaSearchInput(BaseModel):
    query: str = Field(description="The user's question to search for relevant schema information")

class SchemaSearchTool(BaseTool):
    name = "schema_search"
    description = "Search the vector database for relevant schema and table information based on user query"
    args_schema: Type[BaseModel] = SchemaSearchInput
    
    def __init__(self, vector_store, embeddings):
        super().__init__()
        self.vector_store = vector_store
        self.embeddings = embeddings
    
    def _run(self, query: str) -> str:
        """Search for relevant schema information"""
        try:
            results = self.vector_store.similarity_search_with_score(
                f"Which columns in the database are relevant to the following question: {query}", 
                k=3
            )
            
            schema_info = []
            for res in results:
                schema_info.append({
                    "content": res[0].page_content,
                    "score": float(res[1])
                })
            
            return json.dumps(schema_info, indent=2)
        except Exception as e:
            return f"Error searching schema: {str(e)}"

class SQLGenerationInput(BaseModel):
    user_request: str = Field(description="The original user request")
    schema_info: str = Field(description="Relevant schema information in JSON format")

class SQLGenerationTool(BaseTool):
    name = "sql_generation"
    description = "Generate SQL query based on user request and schema information"
    args_schema: Type[BaseModel] = SQLGenerationInput
    
    def __init__(self, sql_generator, join_details):
        super().__init__()
        self.sql_generator = sql_generator
        self.join_details = join_details
    
    def _run(self, user_request: str, schema_info: str) -> str:
        """Generate SQL query"""
        try:
            # Parse schema info back to list format
            schema_list = json.loads(schema_info)
            schema_content = [item["content"] + str(item["score"]) for item in schema_list]
            
            query = self.sql_generator.generate_sql_query(
                user_request=user_request,
                schema_info=schema_content,
                join_details=self.join_details,
                database_type="PostgreSQL"
            )
            return query
        except Exception as e:
            return f"Error generating SQL: {str(e)}"

class QueryValidationInput(BaseModel):
    sql_query: str = Field(description="The SQL query to validate")

class QueryValidationTool(BaseTool):
    name = "query_validation"
    description = "Validate and clean the generated SQL query for safety"
    args_schema: Type[BaseModel] = QueryValidationInput
    
    def _run(self, sql_query: str) -> str:
        """Validate and clean SQL query"""
        try:
            from extract_query import extract_sql_query
            from db.safe_query_analyzer import _safe_sql
            
            # Extract clean SQL
            filtered_query = extract_sql_query(sql_query, strip_comments=True)
            
            # Check safety
            safety_result = _safe_sql(filtered_query)
            
            return json.dumps({
                "cleaned_query": filtered_query,
                "safety_check": safety_result,
                "is_safe": "unsafe" not in safety_result.lower()
            }, indent=2)
        except Exception as e:
            return f"Error validating query: {str(e)}"

class QueryExecutionInput(BaseModel):
    sql_query: str = Field(description="The validated SQL query to execute")

class QueryExecutionTool(BaseTool):
    name = "query_execution"
    description = "Execute the validated SQL query and return results"
    args_schema: Type[BaseModel] = QueryExecutionInput
    
    def __init__(self, query_runner):
        super().__init__()
        self.query_runner = query_runner
    
    def _run(self, sql_query: str) -> str:
        """Execute SQL query"""
        try:
            result = self.query_runner.run(sql_query)
            return str(result)
        except Exception as e:
            return f"Error executing query: {str(e)}"
