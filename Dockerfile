# ============================================
# Stage 1: Build Frontend
# ============================================
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Copy package files first for layer caching
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies (using legacy peer deps due to Vite version conflict)
RUN npm ci --ignore-scripts --legacy-peer-deps

# Copy frontend source
COPY frontend/ .

# Build production bundle (uses .env.production for VITE_API_URL)
RUN npm run build


# ============================================
# Stage 2: Python Backend + Serve Frontend
# ============================================
FROM python:3.13-slim

LABEL maintainer="ByteIQ" \
      service="lendfoundry-chatbot" \
      description="Unified LendFoundry Chatbot API with React frontend"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY unified_api.py .
COPY app_logger.py .
COPY redshift_logger.py .
COPY ui.py .
COPY services/ ./services/
COPY lf_assist/ ./lf_assist/
COPY db_assist/ ./db_assist/
COPY doc_assist/ ./doc_assist/
COPY viz_assist/ ./viz_assist/

# Copy built frontend from Stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Copy .env.example as reference (actual .env is mounted at runtime)
COPY .env.example .env.example

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/.cache && \
    chown -R appuser:appuser /app/.cache

USER appuser

# Expose backend API port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the unified API server (production: no reload)
CMD ["uvicorn", "unified_api:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
