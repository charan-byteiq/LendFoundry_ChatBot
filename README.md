# Combined Chatbot Interface

## Overview

This project provides a unified chat interface for two distinct AI-powered chatbot backends: a Document Assistant for querying PDF files and a Database Assistant for querying a database using natural language. The frontend is built with Streamlit, providing a seamless user experience for interacting with both services from a single application.

## Features

-   **Unified Interface**: A single, clean chat UI for two different chatbot backends.
-   **Chatbot Selection**: Easily switch between the "Document Assistant" and "Database Assistant" via a sidebar menu.
-   **Document Analysis**: Upload a PDF file and ask questions about its content. The state is managed per-session for the uploaded document.
-   **Natural Language Database Querying**: Ask complex questions in plain English to query a connected database.

## Architecture

The application is composed of three main services that run concurrently:

1.  **Document Chatbot Backend**: A FastAPI server located in the `new/` directory that handles PDF uploads and document-related questions. It runs on port `8000`.
2.  **Database Chatbot Backend**: A FastAPI server located in the `src/` directory that processes natural language questions, converts them to SQL, executes them, and returns a natural language response. It runs on port `8001`.
3.  **Unified Frontend**: A Streamlit application (`unified_ui.py`) that serves as the user-facing client for both backends. It runs on port `8501`.

---

## Getting Started

### Prerequisites

-   Docker
-   An environment file with your API keys (see Configuration section).

### Configuration

1.  Create a file named `.env` in the root of the project.
2.  Copy the contents of `.env.example` into your new `.env` file.
3.  Replace the placeholder values with your actual credentials (e.g., your `GOOGLE_API_KEY`).

### Running with Docker (Recommended)

Using Docker is the simplest way to run the entire application, as it handles the setup of all three services.

1.  **Build the Docker image:**
    ```bash
    docker build -t combined-chatbot .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run -p 8000:8000 -p 8001:8001 -p 8501:8501 -v ./.env:/app/.env combined-chatbot
    ```
    *   This command maps the necessary ports and mounts your local `.env` file into the container.

3.  **Access the UI:**
    Open your web browser and navigate to `http://localhost:8501`.

### Running Locally (Alternative)

If you prefer to run the services manually without Docker, you will need to open three separate terminals.

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Terminal 1: Start the Document Chatbot Backend**
    ```bash
    uvicorn new.main:app --host 127.0.0.1 --port 8000
    ```

3.  **Terminal 2: Start the Database Chatbot Backend**
    ```bash
    uvicorn src.api:app --host 127.0.0.1 --port 8001
    ```

4.  **Terminal 3: Start the Unified UI**
    ```bash
    streamlit run unified_ui.py
    ```

---

## How to Use

1.  **Select an Assistant**: Use the sidebar to choose between the "Database Assistant" and the "Document Assistant".
2.  **For the Database Assistant**: Simply type your question into the chat input at the bottom and press Enter.
3.  **For the Document Assistant**:
    *   First, use the file uploader in the sidebar to upload a PDF document.
    *   Once the file is successfully uploaded, the chat input at the bottom will become active.
    *   Type your questions about the document and press Enter.
