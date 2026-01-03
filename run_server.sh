#!/bin/bash
# Script to run LightRAG Server with Gemini configuration

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Activate Virtual Environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set model environment variables (since CLI flags are not supported in this version)
export LLM_MODEL="gemini-2.5-flash"
export EMBEDDING_MODEL="gemini-embedding-001"

echo "🚀 Starting LightRAG Server..."
echo "📂 Data Directory: ./lightrag_data"
echo "🤖 LLM Model: $LLM_MODEL"
echo "📐 Embedding Model: $EMBEDDING_MODEL"

# Run Server
# We use CLI flags for bindings and working-dir, environment variables for model names
lightrag-server \
    --working-dir ./lightrag_data \
    --llm-binding gemini \
    --embedding-binding gemini
