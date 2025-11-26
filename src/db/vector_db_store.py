from langchain_postgres import PGVector
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

COLLECTION_NAME = os.getenv("COLLECTION_NAME")
PGVECTOR_CONNECTION_STRING = os.getenv("PGVECTOR_CONNECTION_STRING")
CONNECTION_STRING = os.getenv("CONNECTION_STRING")

# Create a connection pool
db_pool = pool.SimpleConnectionPool(1, 10, dsn=CONNECTION_STRING)

def get_db_connection():
    """
    Gets a connection from the pool.
    """
    return db_pool.getconn()

def release_db_connection(conn):
    """
    Releases a connection back to the pool.
    """
    db_pool.putconn(conn)

def collection_exists(conn, collection_name):
    """
    Checks if a collection exists in the database.
    Updated to work with langchain_postgres's unified table structure.
    """
    with conn.cursor() as cur:
        # Check if the collection exists as a row in langchain_pg_collection
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM langchain_pg_collection
                WHERE name = %s
            );
        """, (collection_name,))
        return cur.fetchone()[0]


def get_vector_store(embeddings=None):
    """
    Retrieves the vector store. If the collection exists, it loads it. 
    Otherwise, it returns None.
    """
    conn = get_db_connection()
    try:
        if collection_exists(conn, COLLECTION_NAME):
            if embeddings is None:
                embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            return PGVector(
                collection_name=COLLECTION_NAME,
                connection=PGVECTOR_CONNECTION_STRING,
                embeddings=embeddings,
            )
        else:
            return None
    finally:
        release_db_connection(conn)

def create_vector_store(all_splits, embeddings):
    """
    Creates a new vector store.
    """
    vector_store = PGVector.from_documents(
        documents=all_splits,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        connection=PGVECTOR_CONNECTION_STRING,
    )
    return vector_store

def delete_vector_store():
    """
    Deletes the vector store collection.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS langchain_pg_collection_{COLLECTION_NAME};")
            conn.commit()
    finally:
        release_db_connection(conn)

def store_in_vector_db(all_splits, embeddings, force_recreate=False):
    """
    Stores documents in the vector store.
    If force_recreate is True, the existing vector store will be deleted and a new one will be created.
    Otherwise, it will load the existing vector store or create a new one if it doesn't exist.
    """
    if force_recreate:
        print("Force recreating the vector store.")
        delete_vector_store()
        return create_vector_store(all_splits, embeddings)
    
    vector_store = get_vector_store(embeddings)
    if vector_store:
        print("Loading existing vector store.")
        return vector_store
    else:
        print("Creating a new vector store.")
        return create_vector_store(all_splits, embeddings)