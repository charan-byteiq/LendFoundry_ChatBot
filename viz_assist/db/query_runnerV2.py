from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, Any
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder

load_dotenv()


class RedshiftQueryInput(BaseModel):
    """Input schema for Redshift SQL query tool."""
    sql_query: str = Field(description="The SQL query to execute on Redshift database")


class RedshiftSQLTool(BaseTool):
    """Custom tool for executing SQL queries on Redshift via SSH tunnel."""
    
    name: str = "redshift_sql_query"
    description: str = "Execute SQL queries on Redshift database through SSH tunnel and return results"
    args_schema: Type[BaseModel] = RedshiftQueryInput

    def _run(self, sql_query: str, run_manager: Optional[Any] = None) -> str:
        """Execute SQL query on Redshift."""
        conn = None
        tunnel = None
        try:
            conn, tunnel = self._get_connection()
            
            # Use pandas read_sql_query for SELECT queries
            if sql_query.strip().lower().startswith("select"):
                df = pd.read_sql_query(sql_query, conn)
                if df.empty:
                    return "Query executed successfully but returned no results."
                result_str = f"Query returned {len(df)} rows:\n\n"
                result_str += df.to_string(index=False, max_rows=50)
                if len(df) > 50:
                    result_str += f"\n\n... and {len(df) - 50} more rows"
                return result_str
            else:
                # For non-SELECT queries, run using cursor
                with conn.cursor() as cur:
                    cur.execute(sql_query)
                    conn.commit()
                return "Query executed successfully."
        
        except Exception as e:
            return f"Error executing query: {str(e)}"
        
        finally:
            if conn is not None:
                conn.close()
            if tunnel is not None:
                tunnel.stop()
    
    async def _arun(self, sql_query: str, run_manager: Optional[Any] = None) -> str:
        """Async version calls sync method."""
        return self._run(sql_query, run_manager)

    def _get_connection(self):
        """Create a connection to Redshift through an SSH tunnel with debug prints."""
        # Load SSH config
        ssh_host = os.getenv("SSH_HOST")
        ssh_port = int(os.getenv("SSH_PORT", 22))
        ssh_user = os.getenv("SSH_USER")
        ssh_private_key = os.getenv("SSH_PRIVATE_KEY_PATH")
        ssh_password = os.getenv("SSH_PASSWORD")

        # Load Redshift config
        redshift_host = os.getenv("REDSHIFT_HOST")
        redshift_port = int(os.getenv("REDSHIFT_PORT", 5439))
        redshift_db = os.getenv("REDSHIFT_DBNAME")
        redshift_user = os.getenv("REDSHIFT_USER")
        redshift_password = os.getenv("REDSHIFT_PASSWORD")

        if not all([ssh_host, ssh_user, redshift_host, redshift_db, redshift_user, redshift_password]):
            raise Exception("Missing one or more required environment variables for SSH or Redshift.")

        # Start SSH tunnel
        tunnel = SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_username=ssh_user,
            ssh_pkey=ssh_private_key if ssh_private_key else None,
            ssh_password=ssh_password if ssh_password else None,
            remote_bind_address=(redshift_host, redshift_port),
            local_bind_address=("127.0.0.1", 0)  # random local port
        )
        tunnel.start()

        local_port = tunnel.local_bind_port

        # Connect to Redshift through the local forwarded port
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=local_port,
            dbname=redshift_db,
            user=redshift_user,
            password=redshift_password,
            sslmode='require'
        )
        return conn, tunnel

    def run(self, query: str) -> str:
        """Convenience synchronous method for direct execution."""
        return self._run(query)
