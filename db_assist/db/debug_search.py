import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import GoogleGenerativeAIEmbeddings

emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", output_dimensionality=3072)

# Test embed_query vs embed_documents dimensions
q_vec = emb.embed_query("test query about loans")
d_vec = emb.embed_documents(["test document about loans"])[0]
print(f"embed_query dim: {len(q_vec)}")
print(f"embed_documents dim: {len(d_vec)}")

# Check task_type settings
print(f"task_type attribute: {getattr(emb, 'task_type', 'NOT SET')}")

# Now test the actual PGVector similarity search
from db_assist.db.vector_db_store import get_vector_store
vs = get_vector_store()
print(f"\nVector store embeddings model: {vs.embeddings.model}")
print(f"Vector store embeddings class: {type(vs.embeddings)}")

# Try performing the actual similarity search
try:
    results = vs.similarity_search_with_score("Show me loan amount by state", k=5)
    print(f"\nSearch SUCCESS: got {len(results)} results")
    for doc, score in results:
        print(f"  Score: {score:.4f}, Content: {doc.page_content[:80]}...")
except Exception as e:
    print(f"\nSearch FAILED: {e}")
