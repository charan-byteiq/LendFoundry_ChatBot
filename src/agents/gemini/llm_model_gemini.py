import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class SQLQueryGenerator:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Base system prompt for SQL generation
        self.base_system_prompt = """[LendFoundry SQL Generation] You are an expert SQL developer specializing in Amazon Redshift. Generate accurate, efficient, and production-ready SQL queries based strictly on user requests.

                                        ### Core Requirements

                                        **1. Valid SQL Only**
                                        - Return syntactically correct SQL that executes without errors
                                        - Use Redshift-compatible syntax and functions
                                        - Default to ANSI SQL standards when Redshift-specific features aren't needed

                                        **2. Clean Output Format**
                                        - Return only the SQL query without explanations unless specifically requested
                                        - No markdown formatting, prefixes, or code fences
                                        - Use proper indentation and consistent spacing

                                        **3. Query Structure**
                                        - Use explicit column names instead of SELECT * unless instructed otherwise
                                        - Apply meaningful table aliases for joins and subqueries
                                        - Structure complex queries with clear logical flow

                                        **4. Schema Compliance**
                                        - Reference tables using full schema qualification: schema_name.table_name
                                        - Never use imaginary columns, tables, or schemas
                                        - Ask for clarification if schema information is insufficient

                                        **5. Join Optimization**
                                        - Use only necessary joins relevant to the query requirements
                                        - Do not perform inter schema joins
                                        - Prefer INNER JOINs over implicit joins for clarity
                                        - Choose appropriate join types (LEFT, RIGHT, FULL) based on data requirements

                                        **6. Performance Considerations**
                                        - Write index-friendly WHERE clauses
                                        - Use efficient filtering conditions early in the query
                                        - Avoid unnecessary subqueries when simpler alternatives exist
                                        - Leverage Redshift's columnar storage with appropriate column selection

                                        **7. Safety Guidelines**
                                        - Default to read-only SELECT queries
                                        - Generate DDL/DML (INSERT, UPDATE, DELETE, DROP) only when explicitly requested
                                        - Include appropriate WHERE clauses to prevent accidental full-table operations

                                        **8. Redshift-Specific Features**
                                        - Use Redshift date functions (DATEADD, DATEDIFF, etc.) for date manipulations
                                        - Leverage window functions and analytical functions when appropriate
                                        - Apply Redshift-specific aggregate functions where beneficial

                                        **9. Context Awareness**
                                        - Use provided chat history to resolve ambiguities and follow-up questions
                                        - Maintain consistency with previous queries in the conversation
                                        - Build upon established table relationships and naming conventions

                                        **10. Code Quality**
                                        - Use consistent naming conventions for aliases
                                        - Ensure queries are readable and maintainable

                                        Your output should be clean, properly formatted SQL ready for immediate execution in a Redshift environment."""

    
    def generate_sql_query(self, user_request, table_info="", schema_info = "", join_details: str = "", database_type="PostgreSQL", max_tokens=1000):
        """
        Generate SQL query based on user request and optional schema information
        """
        try:
            # Construct the full prompt
            prompt = f"""{self.base_system_prompt}

                    Database Type: {database_type}
                    Schema Information:
                    {schema_info}
            
                    Table Information:
                    {table_info}
                    
                    join Details: {join_details}

                    User Request: {user_request}

                    Generate the appropriate SQL query:
                    
                    If question is : Can you provide the number of borrowers who have a total outstanding amount greater than 50000?
                    Query should look something like: SELECT
                                                        COUNT(DISTINCT lo.borrowerid)
                                                    FROM
                                                        fl_lms.loan_filters AS lf
                                                    JOIN
                                                        fl_lms.loan_onboarding AS lo ON lf.loannumber = lo.loannumber
                                                    WHERE
                                                        lf.pbot_totaloutstanding > 50000;
                    
                    if question is : How many loans were onboarded in the last 5 months?
                    Query should look something like: SELECT
                                                        COUNT(DISTINCT lo.loannumber)
                                                    FROM
                                                        fl_lms.loan_onboarding AS lo
                                                    WHERE
                                                        lo.loanonboardeddate >= DATE_TRUNC('month', DATEADD(month, -5, CURRENT_DATE));

                    If question is : What is the total number of loans?
                    Query should look something like: SELECT
                                                        COUNT(DISTINCT lo.borrowerid)
                                                    FROM
                                                        fl_lms.loan_onboarding AS lo
                                                    JOIN
                                                        fl_lms.loan_filters AS lf
                                                        ON lo.loannumber = lf.loannumber
                                                    WHERE
                                                        lf.loanamount > 20000;
                    """
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2048
                ),
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE",
                    },
                ]
            )
            
            if not response.candidates or response.candidates[0].finish_reason == 2:
                logging.warning("Model returned an empty response for SQL generation or hit the token limit.")
                return None

            if response.text:
                return response.text.strip()
            else:
                logging.warning("Model returned an empty response for SQL generation.")
                return None
            
        except Exception as e:
            logging.error(f"Error generating SQL: {e}")
            return None
