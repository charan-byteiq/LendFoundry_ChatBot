from lf_assist.app.chunk_loader import load_chunks, save_chunks_to_json
from lf_assist.app.qdrant_store import upsert_chunks
import os
import json

pdf_path = "data/New_LMS_Manual_Chatbot.pdf"
json_path = "data/lms_chunks.json"

# Step 1: Extract from PDF and save as JSON
if not os.path.exists(json_path):
    chunks = load_chunks(pdf_path)
    save_chunks_to_json(chunks, json_path)
else:
    with open(json_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

# Step 2: Upload to Qdrant
upsert_chunks(chunks)
