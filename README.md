# LendFoundry Unified Chatbot

## Overview

An intelligent, unified chat interface powered by multiple specialized AI assistants. The system features a **Unified API Router** that automatically classifies user queries and routes them to the appropriate backend service. Includes both a **React + Vite frontend** and a legacy **Streamlit UI**.

## Features

- **Intelligent Query Routing**: Automatic classification using Google Gemini AI
- **Company Knowledge (LF Assist)**: RAG-based Q&A using Qdrant vector database
- **Document Q&A (Doc Assist)**: PDF analysis using Google Gemini
- **Database Assistant (DB Assist)**: Natural language to SQL with LangGraph
- **Visualization Assistant (Viz Assist)**: Charts and data visualization
- **Scope Guard**: Polite deflection for out-of-scope queries
- **Full Swagger Documentation**: All endpoints documented at `/docs`
- **Session Management**: Conversation history across interactions

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Unified Docker Container (Port 8001)               │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐ │
│  │  React SPA       │  │  Unified API Router (FastAPI)        │ │
│  │  (Static assets) │  │  (Routes to multiple backends)       │ │
│  └────────┬─────────┘  └───────────────┬──────────────────────┘ │
└───────────┼────────────────────────────┼────────────────────────┘
            │                            │
            ▼                            ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│  LF Assist   │ │Doc Assist│ │DB Assist │ │ Viz Assist   │
│  /lf-assist  │ │/doc-assist│ │/db-assist│ │ /viz-assist  │
│  Company KB  │ │ PDF Q&A  │ │ SQL Gen  │ │ Charts/Data  │
└──────────────┘ └──────────┘ └──────────┘ └──────────────┘
           │                        │             │
           ▼                        ▼             ▼
┌──────────────┐           ┌──────────────────────────┐
│    Qdrant    │           │  PostgreSQL / Redshift   │
│  (Port 6333) │           │     (Port 5432)          │
└──────────────┘           └──────────────────────────┘
```

### Services

| Service | Directory | Port | Description |
|---------|-----------|------|-------------|
| **Unified API** | `unified_api.py` | 8001 | Central router with Gemini classification |
| **LF Assist** | `lf_assist/` | - | Company knowledge RAG |
| **Doc Assist** | `new/` | - | PDF document Q&A |
| **DB Assist** | `src/` | - | Natural language SQL |
| **Viz Assist** | `viz_assist/` | - | Data visualization |
| **React Frontend** | `frontend/` | 5174 | Modern chat UI |
| **Streamlit UI** | `ui.py` | 8501 | Legacy chat UI |

---

## Quick Start

### Prerequisites

- **Docker Desktop** (Must be running for containerized deployment)
- **Google API Key** with Gemini access 
- **PostgreSQL** for database storage [Download](https://www.postgresql.org/download/)
- **PGVector** for embedding storage [Download](https://github.com/pgvector/pgvector)

### 1. Clone and Configure

```bash
git clone <repository-url>
cd LendFoundry_ChatBot

# Create environment file
cp .env.example .env
# Edit .env with your API keys (Use host.docker.internal for local DBs)
```

### 2. Run with Docker Compose

The simplest way to run the application is using the provided Docker configuration. This builds both the React frontend and the Python backend into a single unified container:

```bash
docker compose up --build
```

Access the application at:
- **Frontend UI**: `http://localhost:8001`
- **Swagger API Docs**: `http://localhost:8001/docs`

---

### Local Development (Without Docker)

If you wish to run the services separately for active development:

**Terminal 1: Backend API**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn unified_api:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2: React Frontend**
```bash
cd frontend
npm install
npm run dev
```


### 4. Configuration

### Environment Variables (`.env`)

```env
# Required: Google Gemini API Key
GOOGLE_API_KEY="your_gemini_api_key_here"

# PostgreSQL (for DB/Viz Assist)
# NOTE: If using Docker and running Postgres locally on Windows, 
# use 'host.docker.internal' instead of 'localhost'
POSTGRES_HOST=host.docker.internal
POSTGRES_PORT=5432
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=chatbot_pass
POSTGRES_DB=chatbot_db

# Qdrant (for LF Assist)
QDRANT_URL="http://localhost:6333"
QDRANT_COLLECTION="lf_chunks"

# Optional: AWS Redshift
REDSHIFT_HOST="your_redshift_host"
REDSHIFT_USER="your_redshift_user"
REDSHIFT_PASSWORD="your_redshift_password"
REDSHIFT_DATABASE="your_database"
REDSHIFT_PORT=5439
```

**Core packages:**
- `react`, `react-dom` - UI framework
- `vite` - Build tool
- `tailwindcss` - Styling
- `shadcn/ui` components - UI library
- `recharts`, `chart.js` - Charting
- `axios` - HTTP client
- `typescript` - Type safety

---

## Query Routing

The system automatically classifies and routes queries:

| Query Type | Backend | Example |
|------------|---------|---------|
| Company policies | **lf_assist** | "How do I apply for a loan?" |
| PDF questions | **doc_assist** | "What's the interest rate in this document?" |
| Data lookups | **db_assist** | "Show loan #12345 status" |
| Visualizations | **viz_assist** | "Chart loan amounts by state" |
| Off-topic | **scope_guard** | "What's the weather?" |

**Keywords that trigger visualization:**
- chart, graph, plot, visualize
- trend, compare, distribution
- show me, display

---

