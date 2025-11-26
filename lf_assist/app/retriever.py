# app/retriever.py
from lf_assist.app.qdrant_store import search_chunks, get_chunks_by_tags

def get_relevant_chunks(query: str, tags: list[str] = None, memory=None, top_k: int = 100) -> list[str]:
    """
    Retrieve relevant document chunks from Qdrant using both semantic query search
    and optional tag filtering. Falls back to query-only search if tags return no matches.

    Args:
        query (str): The user query.
        tags (list[str], optional): List of tags to filter search. Defaults to None.
        memory: ConversationBufferMemory instance (optional) to add recent history context.
        top_k (int): Number of top results to retrieve per search type.

    Returns:
        list[str]: A list of relevant chunk contents.
    """

    # 1️⃣ Optional: Include recent conversation history for vague follow-ups
    if memory and memory.chat_memory.messages:
        history_text = " ".join(m.content for m in memory.chat_memory.messages[-2:])
        search_query = f"{history_text} {query}"
    else:
        search_query = query

    print(f"\n🔍 Running semantic search for query: '{search_query}'")

    # 2️⃣ Always do semantic search based on the query
    query_results = search_chunks(search_query, top_k=top_k)
    print(f"   📄 Semantic search returned {len(query_results)} results")

    # 3️⃣ Tag-based search (if tags provided)
    tag_results = []
    if tags:
        print(f"🏷️ Running tag search for tags: {tags}")
        tag_results = get_chunks_by_tags(tags)
        print(f"   📄 Tag search returned {len(tag_results)} results")
    else:
        print("🏷️ No tags provided for tag search")

    # 4️⃣ Merge and deduplicate results
    seen = set()
    merged_results = []

    for result in query_results + tag_results:
        content = result.get("content") if isinstance(result, dict) else result
        if content not in seen:
            seen.add(content)
            merged_results.append(content)

    # 5️⃣ Fallback: if no merged results, return query-only results
    if not merged_results:
        print("⚠️ No merged results, falling back to query-only results")
        merged_results = [r["content"] for r in query_results]

    print(f"✅ Final merged results: {len(merged_results)} chunks\n")
    return merged_results
