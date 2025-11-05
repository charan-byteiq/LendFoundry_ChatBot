import asyncio
import aiohttp
from langchain_google_genai import GoogleGenerativeAIEmbeddings

async def get_embedding(embedding_model, chunk):
    return embedding_model.embed_query(chunk)

async def generate_embeddings(all_splits):
    embeddings_list = []
    async with aiohttp.ClientSession() as session:
        embeddings_model = GoogleGenerativeAIEmbeddings(session=session, model="models/gemini-embedding-001", task_type="QUESTION_ANSWERING")
        tasks = [get_embedding(embeddings_model, split.page_content) for split in all_splits]
        embeddings_list = await asyncio.gather(*tasks)
    return embeddings_list

