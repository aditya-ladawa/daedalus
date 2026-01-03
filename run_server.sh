#!/bin/bash
# Script to run LightRAG Server with configurable LLM backend
# Configuration is managed in src/rag/config.py (single source of truth)

# Load environment variables from .env if it exists
if [ -f .env ]; then
    set -a  # automatically export all variables
    source <(grep -v '^#' .env | sed 's/^export //' | sed 's/"//g' | sed "s/'//g")
    set +a
fi

# Activate Virtual Environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# =============================================================================
# LOAD CONFIGURATION FROM config.py (Single Source of Truth)
# =============================================================================
echo "📋 Loading configuration from src/rag/config.py..."

# Source configuration from Python config file
eval $(python src/rag/config.py --export-shell)

# Validate that configuration was loaded
if [ -z "$LLM_BACKEND" ]; then
    echo "❌ Failed to load configuration from config.py"
    exit 1
fi

# =============================================================================
# BACKEND-SPECIFIC SETUP
# =============================================================================

if [ "$LLM_BACKEND" = "qwen" ]; then
    # QWEN via OpenRouter - set LLM_BINDING_HOST for lightrag-server
    export LLM_BINDING_HOST="$OPENROUTER_BASE_URL"
    export OPENAI_API_KEY="$OPENROUTER_API_KEY"
    export OPENAI_BASE_URL="$OPENROUTER_BASE_URL"
    export OPENAI_API_BASE="$OPENROUTER_BASE_URL"
    
    echo "🚀 Starting LightRAG Server with QWEN (via OpenRouter)..."
    echo "📂 Data Directory: ./lightrag_data"
    echo "🤖 LLM Model: $LLM_MODEL"
    echo "📐 Embedding Model: $EMBEDDING_MODEL"
    echo "🔗 LLM Host: $LLM_BINDING_HOST"
    echo "🔑 API Key: ${OPENAI_API_KEY:0:20}..."
    
    # Run Server with OpenAI binding for LLM, Gemini for embeddings
    lightrag-server \
        --working-dir ./lightrag_data \
        --llm-binding openai \
        --embedding-binding gemini

elif [ "$LLM_BACKEND" = "gemini" ]; then
    # Gemini - no special setup needed, just use the exported vars
    
    echo "🚀 Starting LightRAG Server with Gemini..."
    echo "📂 Data Directory: ./lightrag_data"
    echo "🤖 LLM Model: $LLM_MODEL"
    echo "📐 Embedding Model: $EMBEDDING_MODEL"
    
    # Run Server with Gemini binding
    lightrag-server \
        --working-dir ./lightrag_data \
        --llm-binding gemini \
        --embedding-binding gemini

else
    echo "❌ Unknown LLM_BACKEND: $LLM_BACKEND"
    echo "   Please set LLM_BACKEND to 'qwen' or 'gemini' in config.py or .env"
    exit 1
fi
