# query_runner.py
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, Any
import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

class RedshiftQueryInput(BaseModel):
    """Input schema for Redshift SQL query tool."""
    sql_query: str = Field(description="The SQL query to execute on Redshift database")

class RedshiftSQLTool(BaseTool):
    """Custom tool for executing SQL queries on Redshift."""
    
    name: str = "redshift_sql_query"
    description: str = "Execute SQL queries on Redshift database and return results"
    args_schema: Type[BaseModel] = RedshiftQueryInput
    
    def _run(
        self,
        sql_query: str,
        run_manager: Optional[Any] = None,
    ) -> pd.DataFrame:
        """Execute the SQL query on Redshift and return DataFrame."""
        try:
            conn = self._get_connection()
            
            # Execute query and return DataFrame
            df = pd.read_sql_query(sql_query, conn)
            conn.close()
            
            return df
            
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")
    
    async def _arun(
        self,
        sql_query: str,
        run_manager: Optional[Any] = None,
    ) -> pd.DataFrame:
        """Async version - for now just call the sync version."""
        return self._run(sql_query, run_manager)
    
    def _get_connection(self):
        """Create a connection to Redshift"""
        try:
            conn = psycopg2.connect(
                host=os.getenv('REDSHIFT_HOST'),
                port=os.getenv('REDSHIFT_PORT', 5439),
                dbname=os.getenv('REDSHIFT_DBNAME'),
                user=os.getenv('REDSHIFT_USER'),
                password=os.getenv('REDSHIFT_PASSWORD'),
                sslmode='require'
            )
            return conn
        except Exception as e:
            raise Exception(f"Failed to connect to Redshift: {str(e)}")
    
    def run(self, query: str) -> pd.DataFrame:
        """Convenience method for direct execution"""
        return self._run(query)
