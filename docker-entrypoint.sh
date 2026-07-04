#!/bin/bash

# Docker entrypoint script for Advanced RAG Application

# Wait for dependencies to be ready
echo "Waiting for dependencies to be ready..."

# Wait for FAISS store (if using)
if [ -n "$FAISS_HOST" ]; then
    echo "Waiting for FAISS store..."
    while ! nc -z $FAISS_HOST $FAISS_PORT; do
        echo "Waiting for FAISS store at $FAISS_HOST:$FAISS_PORT..."
        sleep 2
    done
    echo "FAISS store is ready"
fi

# Wait for Redis (if using)
if [ -n "$REDIS_HOST" ]; then
    echo "Waiting for Redis..."
    while ! nc -z $REDIS_HOST $REDIS_PORT; do
        echo "Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
        sleep 2
    done
    echo "Redis is ready"
fi

# Wait for PostgreSQL (if using)
if [ -n "$POSTGRES_HOST" ]; then
    echo "Waiting for PostgreSQL..."
    while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
        echo "Waiting for PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT..."
        sleep 2
    done
    echo "PostgreSQL is ready"
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p data/feedback logs

# Set permissions
echo "Setting permissions..."
chown -R app:app /app

# Load environment variables if they exist
if [ -f "/app/.env" ]; then
    echo "Loading environment variables..."
    export $(cat /app/.env | xargs)
fi

# Initialize data if configured
if [ -n "$RAG_AUTO_BUILD_INDEX" ] && [ "$RAG_AUTO_BUILD_INDEX" = "true" ]; then
    echo "Initializing data and building vector store..."
    cd /app
    python -c "
import sys
sys.path.append('/app')
from src.rag_pipeline_advanced import rag_pipeline
print('Loading documents and building vector store...')
try:
    rag_pipeline._load_data()
    print('Data loading completed successfully')
except Exception as e:
    print(f'Error loading data: {e}')
    sys.exit(1)
"
fi

# Start the application
echo "Starting Advanced RAG Application..."
echo "Environment variables:"
echo "LANGSMITH_API_KEY: ${LANGSMITH_API_KEY:+'[SET]'}"
echo "LANGSMITH_PROJECT: ${LANGSMITH_PROJECT:+'[SET]'}"
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:+'[SET]'}"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:+'[SET]'}"

# Run the application
exec "$@"