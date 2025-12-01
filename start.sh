#!/bin/bash

echo "Starting Multi-Backend Chatbot System with Docker"

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo " docker-compose is not installed. Please install it first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo ".env file not found. Copying from .env.example..."
    cp .env.example .env
    echo ".env file created. Please update it with your credentials."
    exit 1
fi

# Build and start services
echo "Building Docker images..."
docker-compose build

echo "Starting services..."
docker-compose up -d

echo "Waiting for services to be healthy..."
sleep 10

# Check service status
docker-compose ps

echo ""
echo "Services started!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Access URLs:"
echo "   • Streamlit UI:    http://localhost:8501"
echo "   • Unified API:     http://localhost:8000"
echo "   • LF Assist:       http://localhost:8002"
echo "   • Doc Assist:      http://localhost:8003"
echo "   • DB Assist:       http://localhost:8001"
echo "   • Qdrant:          http://localhost:6333"
echo "   • PostgreSQL:      localhost:5432"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop all:  docker-compose down"
