# Combined Chatbot Interface

## Overview

This project provides a unified chat interface for two distinct AI-powered chatbot backends: a Document Assistant for querying PDF files and a Database Assistant for querying a database using natural language. The frontend is built with Streamlit, providing a seamless user experience for interacting with both services from a single application.

## Features

-   **Unified Interface**: A single, clean chat UI for two different chatbot backends.
-   **Chatbot Selection**: Easily switch between the "Document Assistant" and "Database Assistant" via a sidebar menu.
-   **Document Analysis**: Upload a PDF file and ask questions about its content. The state is managed per-session for the uploaded document.
-   **Natural Language Database Querying**: Ask complex questions in plain English to query a connected database.

## Architecture

The application is composed of five main services that run concurrently:

1.  **Unified API Gateway**: A FastAPI server located in `unified_api.py` that acts as a central entry point, routing requests to the appropriate backend services. It runs on port `8000`.
2.  **Document Chatbot Backend**: A FastAPI server located in the `new/` directory that handles PDF uploads and document-related questions. It runs on port `8003`.
3.  **Database Chatbot Backend**: A FastAPI server located in the `src/` directory that processes natural language questions, converts them to SQL, executes them, and returns a natural language response. It runs on port `8001`.
4.  **LF Assist Backend**: A FastAPI server located in the `lf_assist/` directory that provides specialized assistance. It runs on port `8002`.
5.  **Unified Frontend**: A Streamlit application (`ui.py`) that serves as the user-facing client for all backends. It runs on port `8501`.

---

## Getting Started

### Prerequisites

-   Docker (optional, for containerized deployment)
-   Python 3.10+
-   `pip` (Python package installer)
-   `git` (for cloning the repository)

### Configuration

1.  **Environment Variables**: Create a file named `.env` in the root of the project.
2.  **API Keys**: Copy the contents of `.env.example` into your new `.env` file. **Crucially, replace placeholder values with your actual credentials (e.g., your `GOOGLE_API_KEY`)**. Never hardcode API keys directly into your source code or commit them to version control.
    *   **Important:** Ensure your `GOOGLE_API_KEY` has sufficient quota for the embedding and generative models you intend to use. Refer to the Google AI documentation for quota and billing details.

### Running with Docker (Recommended)

Using Docker is the simplest way to run the entire application, as it handles the setup of all services.

1.  **Build the Docker image:**
    ```bash
    docker build -t combined-chatbot .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 8000:8000 -p 8001:8001 -p 8002:8002 -p 8501:8501 -v ./.env:/app/.env combined-chatbot
    ```
    *   This command maps the necessary ports and mounts your local `.env` file into the container.

3.  **Access the UI:**
    Open your web browser and navigate to `http://localhost:8501`.

### Running Locally (Alternative)

If you prefer to run the services manually without Docker, you will need to open **four separate terminals** or use a process manager.

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *   All project dependencies are now consolidated into a single `requirements.txt` file in the root directory.

2.  **Initialize Vector Database Embeddings (One-time step):**
    ```bash
    python src/db/create_embeddings.py
    ```
    *   This script creates the necessary embeddings from your `table_descriptions_semantic.py` and stores them in your configured vector database. This needs to be run once to set up your RAG system.

3.  **Terminal 1: Start the Unified API Gateway**
    ```bash
    uvicorn unified_api:app --host 127.0.0.1 --port 8000
    ```

4.  **Terminal 2: Start the Document Chatbot Backend**
    ```bash
    uvicorn new.main:app --host 127.0.0.1 --port 8003
    ```

5.  **Terminal 2: Start the Database Chatbot Backend**
    ```bash
    uvicorn src.api:app --host 127.0.0.1 --port 8001
    ```

6.  **Terminal 3: Start the LF Assist Backend**
    ```bash
    uvicorn lf_assist.app.api:app --host 127.0.0.1 --port 8002
    ```

7.  **Terminal 4: Start the UI**
    ```bash
    streamlit run ui.py
    ```

---


