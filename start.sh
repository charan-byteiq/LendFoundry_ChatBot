#!/bin/bash

# Start the Document Chatbot Backend in the background
echo "Starting Document Chatbot Backend..."
uvicorn new.main:app --host 0.0.0.0 --port 8000 &

# Start the Database Chatbot Backend in the background
echo "Starting Database Chatbot Backend..."
uvicorn src.api:app --host 0.0.0.0 --port 8001 &

# Start the LF Assist Chatbot Backend in the background
echo "Starting LF Assist Chatbot Backend..."
(cd lf_assist && uvicorn app.api:app --host 0.0.0.0 --port 8002) &

# Start the Streamlit UI in the foreground
echo "Starting Unified UI..."
streamlit run unified_ui.py --server.port 8501 --server.address 0.0.0.0
