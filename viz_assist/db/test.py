from vector_db_store import get_db_connection, release_db_connection, COLLECTION_NAME

def debug_vector_store():
    """Debug function to check what exists in the database"""
    conn = get_db_connection()
    try:
        print(f"Looking for collection: {COLLECTION_NAME}")
        print(f"Expected table name: langchain_pg_collection_{COLLECTION_NAME}")
        
        # Check all tables in public schema
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename LIKE '%langchain%'
                ORDER BY tablename;
            """)
            tables = cur.fetchall()
            print(f"\nFound {len(tables)} langchain-related tables:")
            for table in tables:
                print(f"  - {table[0]}")
        
        # Check if embedding table exists
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename LIKE '%embedding%'
                ORDER BY tablename;
            """)
            tables = cur.fetchall()
            print(f"\nFound {len(tables)} embedding-related tables:")
            for table in tables:
                print(f"  - {table[0]}")
                
    finally:
        release_db_connection(conn)

# Run the debug function
debug_vector_store()
