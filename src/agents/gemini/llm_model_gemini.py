import os
import logging
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

class SQLQueryGenerator:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")

        self.model = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            max_output_tokens=2048,
            convert_system_message_to_human=True,
        )

        self.base_system_prompt = """You are an expert SQL query generator for Amazon Redshift.
                                    Rules:
                                    1. Use only tables and columns explicitly provided in the schema. Do not infer or assume any additional fields.
                                    2. If the user requests a column, metric, or dimension not present in the schema, respond exactly with: "Column not available in schema."
                                    3. Generate only Redshift-compatible SQL syntax.
                                    4. Never hallucinate table names, column names, or derived fields.
                                    5. When joining tables, only join using columns that exist in the schema and are logically related.
                                    6. Use appropriate aggregations (SUM, COUNT, AVG, etc.) when the query requires them.
                                    7. Apply clear column aliases for readability.
                                    8. Use WHERE clauses to filter data efficiently.
                                    9. Apply ORDER BY and LIMIT only when requested or logically necessary.

                                    Output ONLY the raw SQL query without explanatory text, comments, markdown backticks, or formatting instructions unless a schema violation occurs."""

    @staticmethod
    def _cleanup_sql(text: str) -> str:
        """Remove markdown formatting if present."""
        text = (text or "").strip()
        text = text.replace("``````", "").strip()
        return text

    def generate_sql_query(
        self,
        user_request: str,
        schema_info: str = "",
        join_details: str = "",
        database_type: str = "Redshift",
    ) -> str | None:
        """Generate SQL query based on user request and provided schema information."""
        try:
            user_context = f"""Database Type: {database_type}

                                Schema Information:
                                {schema_info}

                                Join Details:
                                {join_details}

                                User Question:
                                {user_request}

                                Generate the appropriate SQL query:"""

            messages = [
                SystemMessage(content=self.base_system_prompt),
                HumanMessage(content=user_context),
            ]

            ai_msg = self.model.invoke(messages)
            return self._cleanup_sql(ai_msg.content)

        except Exception as e:
            logging.error(f"Error generating SQL: {e}")
            return None
