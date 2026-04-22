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

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        output_dimensionality=3072   
    )
    
    # sanity check
    print("Embedding dimension:", len(embeddings.embed_query("test")))

    print("Starting the process of storing documents in the vector database.")

    vector_store = store_in_vector_db(
        all_splits=documents,
        embeddings=embeddings,
        force_recreate=True   
    )
    
    if vector_store:
        print("Successfully created and stored embeddings in the vector database.")
        print(f"Collection Name: {vector_store.collection_name}")
    else:
        print("Failed to create or store embeddings.")

if __name__ == "__main__":
    create_and_store_embeddings()