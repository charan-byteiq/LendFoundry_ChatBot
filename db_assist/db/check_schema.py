import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("CONNECTION_STRING"))
cur = conn.cursor()

# Check column type definition
cur.execute("""
    SELECT pg_catalog.format_type(a.atttypid, a.atttypmod)
    FROM pg_attribute a
    JOIN pg_class c ON a.attrelid = c.oid
    WHERE c.relname = 'langchain_pg_embedding'
    AND a.attname = 'embedding'
""")
print("Column type:", cur.fetchone())

# Check actual dimensions stored
cur.execute("""
    SELECT c.name, vector_dims(e.embedding), COUNT(*)
    FROM langchain_pg_embedding e
    JOIN langchain_pg_collection c ON e.collection_id = c.uuid
    GROUP BY c.name, vector_dims(e.embedding)
""")
print("Stored dimensions:", cur.fetchall())

# Check all collections
cur.execute("SELECT name, uuid FROM langchain_pg_collection")
print("Collections:", cur.fetchall())

# Check any index definitions on the embedding column
cur.execute("""
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 'langchain_pg_embedding'
""")
print("Indexes:", cur.fetchall())

cur.close()
conn.close()
