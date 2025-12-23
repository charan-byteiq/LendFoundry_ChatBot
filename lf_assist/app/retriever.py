# app/retriever.py
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from lf_assist.app.qdrant_store import search_chunks, get_chunks_by_tags
from logger import logger


def get_relevant_chunks(
    query: str, 
    tags: list[str] = None, 
    chat_history: Optional[Dict[str, Any]] = None, 
    top_k: int = 100
) -> list[str]:
    """
    Retrieve relevant document chunks from Qdrant using both semantic query search
    and optional tag filtering. Falls back to query-only search if tags return no matches.

    Args:
        query (str): The user query.
        tags (list[str], optional): List of tags to filter search. Defaults to None.
        chat_history (dict, optional): Dictionary containing conversation history.
                                      Format: {"chat_history": [messages], "history": "formatted string"}
        top_k (int): Number of top results to retrieve per search type.

    Returns:
        list[str]: A list of relevant chunk contents.
    """

    # 1️⃣ Optional: Include recent conversation history for vague follow-ups
    if chat_history and chat_history.get("chat_history"):
        messages = chat_history["chat_history"]
        
        # Get last 2 messages (last user message and last bot response)
        recent_messages = messages[-2:] if len(messages) >= 2 else messages
        
        # Extract content from messages
        history_text_parts = []
        for msg in recent_messages:
            if isinstance(msg, (HumanMessage, AIMessage)):
                history_text_parts.append(msg.content)
        
        history_text = " ".join(history_text_parts)
        search_query = f"{history_text} {query}"
        logger.debug(f"Using conversation context: {history_text[:100]}...")
    else:
        search_query = query

    logger.debug(f"Running semantic search for query: '{search_query}'")

    # 2️⃣ Always do semantic search based on the query
    query_results = search_chunks(search_query, top_k=top_k)
    logger.debug(f"Semantic search returned {len(query_results)} results")

    # 3️⃣ Tag-based search (if tags provided)
    tag_results = []
    if tags:
        logger.debug(f"Running tag search for tags: {tags}")
        tag_results = get_chunks_by_tags(tags)
        logger.debug(f"Tag search returned {len(tag_results)} results")
    else:
        logger.debug("No tags provided for tag search")

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
        logger.warning("No merged results, falling back to query-only results")
        merged_results = [r["content"] for r in query_results]

    logger.debug(f"Final merged results: {len(merged_results)} chunks")
    return merged_results


def get_relevant_chunks_with_scores(
    query: str, 
    tags: list[str] = None, 
    chat_history: Optional[Dict[str, Any]] = None, 
    top_k: int = 100
) -> list[dict]:
    """
    Enhanced version that returns chunks with their relevance scores.

    Args:
        query (str): The user query.
        tags (list[str], optional): List of tags to filter search.
        chat_history (dict, optional): Dictionary containing conversation history.
        top_k (int): Number of top results to retrieve per search type.

    Returns:
        list[dict]: List of dicts with 'content' and 'score' keys.
    """

    # Include conversation context if available
    if chat_history and chat_history.get("chat_history"):
        messages = chat_history["chat_history"]
        recent_messages = messages[-2:] if len(messages) >= 2 else messages
        
        history_text_parts = []
        for msg in recent_messages:
            if isinstance(msg, (HumanMessage, AIMessage)):
                history_text_parts.append(msg.content)
        
        history_text = " ".join(history_text_parts)
        search_query = f"{history_text} {query}"
    else:
        search_query = query

    print(f"\n🔍 Running semantic search with scores for query: '{search_query}'")

    # Semantic search
    query_results = search_chunks(search_query, top_k=top_k)
    print(f"   📄 Semantic search returned {len(query_results)} results")

    # Tag-based search
    tag_results = []
    if tags:
        print(f"🏷️ Running tag search for tags: {tags}")
        tag_results = get_chunks_by_tags(tags)
        print(f"   📄 Tag search returned {len(tag_results)} results")

    # Merge with scores
    seen = set()
    merged_results = []

    for result in query_results + tag_results:
        if isinstance(result, dict):
            content = result.get("content")
            score = result.get("score", 0.0)
        else:
            content = result
            score = 0.0
        
        if content not in seen:
            seen.add(content)
            merged_results.append({
                "content": content,
                "score": score
            })

    # Sort by score (highest first)
    merged_results.sort(key=lambda x: x["score"], reverse=True)

    print(f"✅ Final merged results: {len(merged_results)} chunks with scores\n")
    return merged_results
