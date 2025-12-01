# Combined Chatbot Interface

## Overview

This project provides an intelligent, unified chat interface powered by multiple specialized AI assistants working together. The system features a **Unified API Router** that automatically classifies user queries and routes them to the appropriate backend service. The frontend is built with Streamlit, providing a seamless user experience with **visual backend indicators** showing which assistant handled each query.

## Features

- **🎯 Intelligent Query Routing**: Automatic classification using Google Gemini AI to route queries to the right assistant
- **📚 Company Knowledge Assistant (LF Assist)**: Answers questions about company policies, procedures, and lending services using RAG with Qdrant vector database
- **📄 Document Q&A Assistant**: Upload PDF files and ask questions about their content using Google Gemini's document understanding
- **💾 Database Assistant**: Natural language database querying with LangGraph agents for complex SQL operations
- **🛡️ Scope Guard**: Politely deflects out-of-scope queries while redirecting users to relevant topics
- **🎨 Visual Backend Indicators**: Color-coded badges show which assistant answered each query
- **💬 Session Management**: Maintains conversation history across interactions
- **🔄 Retry Logic**: Automatic retry with exponential backoff for API failures

## Architecture

The application uses a **microservices architecture** with the following services:

### Core Services

1. **Unified API Router** (`unified_api.py`) - Port `8000`
   - Central entry point for all queries
   - Gemini-powered query classification
   - Routes to appropriate backend with retry logic
   - Health monitoring for all services

2. **LF Assist Backend** (`lf_assist/`) - Port `8002`
   - Company knowledge and policy questions
   - RAG-based retrieval using Qdrant vector database
   - Session-based conversation memory
   - Query tagging and contextual responses

3. **Doc Assist Backend** (`new/`) - Port `8003`
   - PDF document analysis and Q&A
   - Google Gemini document processing
   - Supports documents up to 20 pages and 5MB

4. **DB Assist Backend** (`src/`) - Port `8001`
   - Natural language to SQL conversion
   - LangGraph agent for complex queries
   - Supports PostgreSQL with pgvector and AWS Redshift
   - Semantic table search using embeddings

5. **Streamlit Frontend** (`ui.py`) - Port `8501`
   - Interactive chat interface with backend indicators
   - File upload for document Q&A
   - Session management and history
   - Color-coded assistant badges (green/blue/orange/gray)

### Supporting Services

6. **PostgreSQL with pgvector** - Port `5432`
   - Vector database for DB Assist embeddings
   - Table metadata storage

7. **Qdrant Vector Database** - Port `6333`
   - Vector search for LF Assist RAG
   - Document chunk storage and retrieval

***

## Getting Started

### Prerequisites

- **Docker** and **Docker Compose** (v3.8+) - **Recommended**
- **Python 3.13.7** (for local development)
- **Git** (for cloning the repository)
- **Google API Key** with Gemini access

### Project Structure

```
Combined_Chatbot/
├── docker-compose.yml          # Multi-service orchestration
├── Dockerfile.unified          # Unified API router container
├── Dockerfile.streamlit        # Frontend container
├── unified_api.py              # Router API with classification
├── ui.py                       # Streamlit interface
├── .env                        # Environment variables (create from .env.example)
├── requirements.txt            # Root dependencies
├── lf_assist/                  # Company knowledge backend
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
├── new/                        # Document Q&A backend
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
└── src/                        # Database query backend
    ├── Dockerfile
    ├── requirements.txt
    └── api.py
```

### Configuration

1. **Create Environment File**:
   ```bash
   cp .env.example .env
   ```

2. **Configure Required Variables** in `.env`:
   ```env
   # Required: Google Gemini API Key
   GOOGLE_API_KEY="your_gemini_api_key_here"
   
   # PostgreSQL (auto-configured for Docker)
   POSTGRES_USER=chatbot_user
   POSTGRES_PASSWORD=chatbot_pass
   POSTGRES_DB=chatbot_db
   
   # Qdrant (auto-configured for Docker)
   QDRANT_URL="http://qdrant:6333"
   QDRANT_COLLECTION="your_collection_name"
   
   # Optional: External Redshift connection
   REDSHIFT_HOST="your_redshift_host"
   REDSHIFT_USER="your_redshift_user"
   REDSHIFT_PASSWORD="your_redshift_password"
   ```

3. **Important Notes**:
   - Obtain your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Ensure sufficient API quota for embeddings and generative models
   - Never commit `.env` to version control

***

## Running with Docker Compose (Recommended)

Docker Compose orchestrates all services with proper networking, health checks, and dependencies.

### Quick Start

1. **Start All Services**:
   ```bash
   docker-compose up --build -d
   ```

2. **View Logs**:
   ```bash
   docker-compose logs -f
   ```

3. **Access the Application**:
   - **Streamlit UI**: http://localhost:8501
   - **Unified API Docs**: http://localhost:8000/docs
   - **Health Check**: http://localhost:8000/health

4. **Stop All Services**:
   ```bash
   docker-compose down
   ```

### Management Commands

```bash
# Check service status
docker-compose ps

# View specific service logs
docker-compose logs -f unified_api
docker-compose logs -f lf_assist

# Restart specific service
docker-compose restart db_assist

# Rebuild specific service
docker-compose up --build -d doc_assist

# Clean slate (removes volumes)
docker-compose down -v

# Scale a service (horizontal scaling)
docker-compose up -d --scale lf_assist=3
```

### Service URLs (Docker)

- **Frontend**: http://localhost:8501
- **Unified API**: http://localhost:8000
- **LF Assist**: http://localhost:8002
- **Doc Assist**: http://localhost:8003
- **DB Assist**: http://localhost:8001
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **PostgreSQL**: localhost:5432

***

## Running Locally (Development)

For development without Docker, run each service in a separate terminal.

### Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Vector Database** (one-time):
   ```bash
   python src/db/create_embeddings.py
   ```

### Start Services

**Terminal 1: Unified API Router**
```bash
uvicorn unified_api:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2: LF Assist Backend**
```bash
cd lf_assist
uvicorn app.api:app --host 0.0.0.0 --port 8002 --reload
```

**Terminal 3: Doc Assist Backend**
```bash
cd new
uvicorn app:app --host 0.0.0.0 --port 8003 --reload
```

**Terminal 4: DB Assist Backend**
```bash
cd src
uvicorn api:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 5: Streamlit UI**
```bash
streamlit run ui.py
```

***

## Using the Application

### Query Routing

The system automatically routes queries based on content:

| Query Type | Routes To | Badge Color | Example |
|------------|-----------|-------------|---------|
| Company policies, procedures | **LF Assist** | 🟢 Green | "How do I apply for a loan?" |
| Uploaded document questions | **Doc Assist** | 🔵 Blue | "What interest rate is in this PDF?" |
| Loan data, customer records | **DB Assist** | 🟠 Orange | "Show loan ID 12345 status" |
| Out-of-scope queries | **Scope Guard** | ⚪ Gray | "What's the weather today?" |

### Features

- **Session Continuity**: LF Assist maintains conversation context across multiple exchanges
- **Document Upload**: Click the file uploader in the sidebar to upload PDFs (max 20 pages, 5MB)
- **Backend Indicators**: Each response shows a colored badge indicating which assistant answered
- **Query Tags**: LF Assist responses include relevant topic tags
- **Clear History**: Reset conversation using the sidebar button

### Example Interactions

**Company Knowledge**:
```
User: "What are the types of loans?"
LF Assist (🟢): "Lendfoundry LMS is a multi-product servicing platform that supports various loan types. These include unsecured and secured term loans with different schedule types, Cash Advances, and Lines of Credit (LOCs). Additionally, the system also supports Supply Chain Financing (SCF) loans, which are non-revolving term loans that can have multiple invoices associated with a single borrower."
```

**Document Q&A**:
```
User: [uploads contract.pdf] "What is the date of birth of the person"
Doc Assist (🔵): "The date of birth of the person is 20/12/1990"
```

**Database Query**:
```
User: "what are the number of loans onboarded in the last 10 months"
DB Assist (🟠): "There have been 20 loans onboarded in the last 10 months."
```

***

## Monitoring and Debugging

### Health Checks

All services include health checks accessible via:
```bash
curl http://localhost:8000/health
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service with timestamps
docker-compose logs -f --timestamps lf_assist

# Last 100 lines
docker-compose logs --tail=100 unified_api
```

### Common Issues

**Issue**: Service won't start
```bash
# Check logs
docker-compose logs <service_name>

# Restart service
docker-compose restart <service_name>
```

**Issue**: Connection refused
```bash
# Verify services are running
docker-compose ps

# Check network
docker network inspect chatbot_network
```

**Issue**: Out of memory
```bash
# Check resource usage
docker stats

# Restart services
docker-compose restart
```

***

## Production Deployment

### Security Checklist

- [ ] Set strong PostgreSQL passwords
- [ ] Restrict CORS origins in FastAPI services
- [ ] Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- [ ] Enable HTTPS with reverse proxy (nginx, Traefik)
- [ ] Set resource limits in docker-compose
- [ ] Enable Docker logging drivers
- [ ] Regular security updates

### Scaling

```bash
# Scale specific services
docker-compose up -d --scale lf_assist=3 --scale db_assist=2

# Use nginx for load balancing
# Configure docker-compose.prod.yml with replicas
```

***

## Development

### Adding New Backends

1. Create new service directory with Dockerfile
2. Add service to `docker-compose.yml`
3. Update classification logic in `unified_api.py`
4. Add backend config to `ui.py` `BACKEND_CONFIG`

### Testing

```bash
# Test unified API
curl -X POST http://localhost:8000/chat \
  -F "message=How do I apply for a loan?" \
  -F "session_id=test123"

# Test specific backend
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"What are interest rates?","session_id":"test"}'
```

***

## License

This project is proprietary software developed by ByteIQ.

## Support

For issues or questions, contact the development team or create an issue in the repository.

***

**Built with**: FastAPI -  Streamlit -  Google Gemini -  LangChain - LangGraph -  Qdrant -  PostgreSQL -  Docker
