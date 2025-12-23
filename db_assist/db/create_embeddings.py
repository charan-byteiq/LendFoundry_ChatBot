import os
import sys
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.table_descriptions_semantic import documents
from db.vector_db_store import store_in_vector_db

# Load environment variables
load_dotenv()

def create_and_store_embeddings():
    """
    Initializes the embedding model, loads the documents, and stores them in the vector database.
    """
    print("Initializing embedding model...")
    # Ensure you have GOOGLE_API_KEY in your .env file
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    print("Starting the process of storing documents in the vector database.")
    # The `documents` are imported from the semantic descriptions file
    # `force_recreate=True` will delete any existing collection and create a new one.
    # Set to `False` if you want to load an existing store or create one if it doesn't exist.
    vector_store = store_in_vector_db(all_splits=documents, embeddings=embeddings, force_recreate=True)
    
    if vector_store:
        print("Successfully created and stored embeddings in the vector database.")
        print(f"Collection Name: {vector_store.collection_name}")
    else:
        print("Failed to create or store embeddings.")

if __name__ == "__main__":
    # This allows the script to be run directly to populate the vector store
    create_and_store_embeddings()
