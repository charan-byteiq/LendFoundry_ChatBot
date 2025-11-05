# from llm_model1 import SQLQueryGenerator
from llm_model import SQLQueryGenerator
from extract_query import extract_sql_query
from safe_query_analyzer import _safe_sql
from typing import Any, Dict

class MySQLGeneratorTool:
    """Wraps your existing SQLQueryGenerator logic into a callable tool/step."""
    name = "sql_generator"
    description = "Generate a safe SQL query from user request + schema info + join details."

    def __init__(self, join_details):
        self.join_details = join_details

    def _run(self, tool_input: Dict[str, Any]) -> str:
        user_request = tool_input["user_request"]
        schema_info = tool_input["schema_info"]
        # call your existing pipeline
        query = SQLQueryGenerator().generate_sql_query(
            user_request=user_request,
            schema_info=schema_info,
            join_details=self.join_details,
            database_type="PostgreSQL"
        )
        filtered = extract_sql_query(query, strip_comments=True)
        safe = _safe_sql(filtered)
        return safe

    async def _arun(self, tool_input: Dict[str, Any]) -> str:
        return self._run(tool_input)
