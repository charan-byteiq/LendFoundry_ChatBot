import boto3
import json
import logging
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError


load_dotenv()

class SQLQueryGenerator:
    def __init__(self, region_name='us-east-1'):
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=region_name
        )
        self.model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        
        # Base system prompt for SQL generation
        self.base_system_prompt = """
                                    You are an expert SQL developer. Your task is to generate accurate, efficient, and production-ready SQL queries based strictly on user requests.

                                    Follow these rules:

                                    1. Valid SQL Only  
                                    - Always return syntactically valid SQL that can run without errors.  
                                    - Use the appropriate SQL dialect based on context (default to ANSI SQL if unsure).

                                    2. Clean Output  
                                    - Return only the SQL query unless the user specifically asks for explanations or commentary.  
                                    - Do not include any prefixes like “Here is the SQL:” or markdown formatting (no ```sql fences).

                                    3. Formatting & Style  
                                    - Use proper indentation and spacing.  
                                    - Use explicit column names instead of SELECT * unless instructed otherwise.  
                                    - Use table aliases for readability in joins or subqueries.

                                    4. Comments & Readability  
                                    - Include brief inline comments for complex expressions, joins, or subqueries.  
                                    - Omit comments for simple queries unless clarification is helpful.

                                    5. Performance & Best Practices  
                                    - Apply LIMIT clauses to large queries where appropriate.  
                                    - Avoid unnecessary subqueries or computations.  
                                    - Use WHERE, JOIN, and INDEX-friendly filtering to optimize performance.

                                    6. Safety First  
                                    - Never generate DDL or DML (e.g. INSERT, UPDATE, DELETE, DROP) unless explicitly requested.  
                                    - Default to read-only SELECT queries unless otherwise stated.

                                    7. Schema Awareness  
                                    - Strictly do not use imaginary columns or tables out of context. If schema or context information is insufficient, ask for more details instead of guessing.

                                    8. Join Usage  
                                    - Use only the joins which are required for the query and relevant to the context.

                                    9. Schema Information
                                    - Look at the schema from which the table belongs and accordingly mention schema in the query.
                                    for example: SchemaName.TableName.ColumnName
                                    Your output should be clean, readable, and ready to run in a SQL console.
                                    """
    
    def generate_sql_query(self, user_request, table_info="", schema_info = "", join_details: str = "", database_type="PostgreSQL", max_tokens=1000):
        """
        Generate SQL query based on user request and optional schema information
        """
        try:
            # Construct the full prompt
            prompt = f"""Database Type: {database_type}
                    Schema Information:
                    {schema_info}
            
                    Table Information:
                    {table_info}
                    
                    join Details: {join_details}

                    User Request: {user_request}

                    Generate the appropriate SQL query:"""
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "system": self.base_system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
            
            response = self.bedrock_runtime.invoke_model(body=body, modelId=self.model_id)
            response_body = json.loads(response.get('body').read())
            
            return response_body['content'][0]['text'].strip()
            
        except ClientError as err:
            logging.error(f"Error generating SQL: {err.response['Error']['Message']}")
            return None

