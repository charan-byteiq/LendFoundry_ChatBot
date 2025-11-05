import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

# Adjust imports to be relative to the 'src' directory
from src.agents.bedrock.sql_langgraph_agent_bedrock import SQLLangGraphAgentBedrock
from src.db.vector_db_store import store_in_vector_db
from src.db.query_runner import RedshiftSQLTool

# Import schema and document information
# Assuming table_updated_desc.py is in the root or accessible in PYTHONPATH
from table_updated_desc import all_tables as documents, join_details, schema_info

# Load environment variables from .env file
load_dotenv()

# Configuration
# Ensure AWS credentials are configured in your environment (e.g., via ~/.aws/credentials or environment variables)
# GOOGLE_API_KEY is used for embeddings
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def main():
    """
    Main function to initialize and run the Bedrock SQL LangGraph agent.
    """
    print("Initializing Bedrock SQL Agent...")

    # 1. Initialize Embeddings (using Google's for consistency)
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)
        print("Embeddings initialized successfully.")
    except Exception as e:
        print(f"Error initializing embeddings: {e}")
        return

    # 2. Prepare documents and Vector Store
    try:
        # Flatten the list of documents if it's nested
        flat_splits = [d for doc_list in documents for d in (doc_list if isinstance(doc_list, list) else [doc_list])]
        
        # Create or load the vector store
        # Set force_recreate=True to delete the old vector store and create a new one.
        vector_store = store_in_vector_db(flat_splits, embeddings, force_recreate=False)
        print("Vector store created successfully.")
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return

    # 3. Initialize Query Runner (optional)
    # Replace with your actual Redshift connection details if you want to execute queries
    query_runner = None
    # try:
    #     query_runner = RedshiftSQLTool()
    #     print("Redshift query runner initialized.")
    # except Exception as e:
    #     print(f"Could not initialize Redshift query runner: {e}")
    #     print("Query execution will be skipped.")

    # 4. Initialize the Bedrock Agent
    try:
        bedrock_agent = SQLLangGraphAgentBedrock(
            vector_store=vector_store,
            embeddings=embeddings,
            join_details=join_details,
            schema_info=schema_info,
            query_runner=query_runner
        )
        print("Bedrock SQL LangGraph Agent initialized successfully.")
    except Exception as e:
        print(f"Error initializing Bedrock agent: {e}")
        return

    # 5. Process a sample query
    user_question = "give the borrowerids which have dpd more than 20"
    print(f"\nProcessing user question: '{user_question}'")
    
    try:
        result = bedrock_agent.process_query(user_question)
        
        # Print the final result
        print("\n--- Agent Final Result ---")
        print(f"Success: {result.get('success')}")
        if result.get('success'):
            print(f"User Question: {result.get('user_question')}")
            print(f"Cleaned SQL Query: {result.get('cleaned_sql_query')}")
            print(f"Execution Result: {result.get('execution_result', 'N/A')}")
        else:
            print(f"Error: {result.get('error')}")
        print("--------------------------")

    except Exception as e:
        print(f"An error occurred during query processing: {e}")

if __name__ == "__main__":
    main()


