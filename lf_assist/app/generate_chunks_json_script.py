# generate_chunks_json.py

from lf_assist.app.chunk_loader import load_chunks, save_chunks_to_json

pdf_path = "data/New_LMS_Manual_Chatbot.pdf"
json_path = "data/lms_chunks.json"

chunks = load_chunks(pdf_path)
print(f"✅ Extracted {len(chunks)} chunks from PDF.")
save_chunks_to_json(chunks, json_path)
