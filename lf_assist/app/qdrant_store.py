from qdrant_client import QdrantClient
import os

from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from sentence_transformers import SentenceTransformer
import uuid
import requests

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION")

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    prefer_grpc=True
)

model = SentenceTransformer("all-MiniLM-L6-v2")

def set_tags_payload_index():
    url = f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/index"
    headers = {
        "Content-Type": "application/json",
        "api-key": QDRANT_API_KEY
    }
    data = {
        "field_name": "tags",
        "field_schema": "keyword"
    }

    response = requests.put(url, headers=headers, json=data)
    if response.status_code != 200:
        raise Exception(f"❌ Failed to set payload index: {response.text}")
    print("✅ 'tags' payload index created successfully.")

def upsert_chunks(chunks: list[dict]):
    existing = [col.name for col in client.get_collections().collections]
    if QDRANT_COLLECTION in existing:
        client.delete_collection(collection_name=QDRANT_COLLECTION)

    client.recreate_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

    set_tags_payload_index()

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=model.encode(chunk["content"]).tolist(),
            payload=chunk
        )
        for chunk in chunks
    ]

    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print(f"✅ Successfully upserted {len(points)} chunks to Qdrant.")

def search_chunks(query: str, top_k: int = 5, filter_tags: list[str] = None):
    vector = model.encode(query).tolist()

    search_filter = None
    if filter_tags:
        search_filter = Filter(
            should=[
                FieldCondition(
                    key="tags",
                    match=MatchValue(value=tag)
                ) for tag in filter_tags
            ]
        )

    results = client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=vector,
        limit=top_k,
        query_filter=search_filter
    )

    return [hit.payload for hit in results]

# ✅ NEW: Get all chunks matching tags (no vector scoring, no top_k limit)
def get_chunks_by_tags(tags: list[str]) -> list:
    """
    Returns all chunks that match the given tags without top_k limit.
    """
    if not tags:
        return []

    tag_filter = Filter(
        should=[
            FieldCondition(key="tags", match=MatchValue(value=tag))
            for tag in tags
        ]
    )

    scroll_result = client.scroll(
        collection_name=QDRANT_COLLECTION,
        scroll_filter=tag_filter,
        with_payload=True,
        with_vectors=False,
        limit=1000  # adjust this if needed
    )

    return [point.payload for point in scroll_result[0]]
