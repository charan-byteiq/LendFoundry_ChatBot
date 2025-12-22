import os
import logging
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLQueryGenerator:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        
        # Initialize LangChain model with configuration
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.api_key,
            temperature=0,  # Deterministic output for SQL
            max_output_tokens=2048,
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
            }
        )
        
        # Base system prompt for SQL generation
        self.base_system_prompt = """You are an expert SQL query generator for Amazon Redshift, specialized in producing queries  for data visualization tools (charts, dashboards, and reports).
                                    You must strictly follow these rules:
                                    1. Use only the tables and columns explicitly provided in the schema. Do not infer or assume any additional fields.
                                    2. If the user requests a column, metric, or dimension not present in the schema, respond exactly with: "Column not available in schema."
                                    3. Generate only Redshift-compatible SQL syntax.
                                    4. Never hallucinate table names, column names, or derived fields.
                                    5. When joining tables, only join using columns that exist in the schema and are logically related.
                                    6. Optimize queries for visualization use cases:
                                        - Include appropriate aggregations (SUM, COUNT, AVG, etc.) when needed.
                                        - Use GROUP BY for categorical or time-based dimensions.
                                        - Apply clear column aliases suitable for chart labels.
                                        - Use ORDER BY to produce meaningful visual ordering.
                                        - Apply LIMIT where appropriate for previews or top-N visualizations.

                                    Do not include explanatory text, comments, markdown backticks, or formatting instructions.
                                    Return ONLY the raw SQL query unless a schema violation occurs."""

    def generate_sql_query(self, user_request: str, schema_info: str = "", join_details: str = "", database_type: str = "Redshift") -> str:
        """
        Generate SQL query based on user request and provided schema information.
        """
        try:
            # Construct the user-specific context
            user_context = f"""
                                Database Type: {database_type}

                                Schema Information:
                                {schema_info}

                                Join Details:
                                {join_details}

                                User Question: 
                                {user_request}

                                Generate the appropriate SQL query:"""
            # Create message payload
            messages = [
                SystemMessage(content=self.base_system_prompt),
                HumanMessage(content=user_context)
            ]

            # Invoke the model
            response = self.model.invoke(messages)
            
            sql_query = response.content.strip().replace('``````', '').strip()
            
            if not sql_query:
                logger.warning("Model returned an empty response for SQL generation.")
                return None
                
            return sql_query
            
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return None

