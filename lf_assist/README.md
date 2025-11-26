# LMS Chatbot

An AI-powered chatbot designed to interact with LMS (Learning Management System) documents using natural language. It leverages Google Gemini for response generation, Qdrant for vector-based document search, and FastAPI + React for a smooth user experience.

## ✨ Features

- 🤖 Powered by **Google Gemini 2.5 Flash**
- 🧠 Maintains **conversation context** with LangChain memory
- 📄 Supports **DOCX file ingestion** and chunking
- 🔍 Semantic search using **Qdrant** vectorDB + SentenceTransformers
- 💬 REST API + Command-line interface
- 🎨 Clean, React-based web UI
- 🔖 Tag-based query filtering for enhanced relevance

## 🧱 Architecture Overview

User Query
│
├──▶ Tagging (LangChain + prompt)
├──▶ Chunk Retrieval from Qdrant (tag-filtered)
├──▶ Gemini Summarization (with context memory)
└──▶ Final Response



## ⚙️ Backend Setup (FastAPI + Qdrant)

```bash
cd lmschatbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt




##Update config/settings.py:  

QDRANT_URL = "https://dbc589fa-30ef-4b49-bf73-f9c7a19fef5f.us-east4-0.gcp.cloud.qdrant.io"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.-3-pdidG0Ej8pyRTAQGKYLXnhLxcbbbqenbF9mlQJdw"
QDRANT_COLLECTION = "lms_chunks"

GOOGLE_API_KEY = "AIzaSyCFfArIw7pWQ9T7X44NuEGwKxqVP3ZA6Yw"
GEMINI_MODEL = "gemini-2.5-flash"       
 


##Run the chunking and embedding pipeline:

python run.py



##Start the API server:

uvicorn app.api:app --reload



##Frontend Setup (React)

cd lms-chatbot-ui
npm install
npm start
Access UI at http://localhost:3000. Ensure backend is running at http://localhost:8000
