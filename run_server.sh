#!/bin/bash
# Script to run LightRAG Server with configurable LLM backend
# Configuration is loaded from .env file

set -e  # Exit on error

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo "📋 Loading configuration from .env..."
    set -a  # automatically export all variables
    source <(grep -v '^#' .env | sed 's/^export //')
    set +a
else
    echo "❌ .env file not found!"
    exit 1
fi

# Activate Virtual Environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default values (can be overridden by .env or command line args)
WORKING_DIR="${WORKING_DIR:-./lightrag_data_local}"
WORKSPACE="${WORKSPACE:-default}"
LLM_BACKEND="${LLM_BACKEND:-gemini}"
STORAGE_MODE="${STORAGE_MODE:-cloud}"

# =============================================================================
# STORAGE MODE SETUP
# =============================================================================

if [ "$STORAGE_MODE" = "cloud" ]; then
    # Cloud mode: Use Qdrant + Neo4j
    if [ -z "$QDRANT_URL" ] || [ -z "$NEO4J_URI" ]; then
        echo "❌ Cloud storage requires QDRANT_URL and NEO4J_URI in .env"
        exit 1
    fi
    
    # Set LightRAG cloud storage environment variables
    export LIGHTRAG_VECTOR_STORAGE="QdrantVectorDBStorage"
    export LIGHTRAG_GRAPH_STORAGE="Neo4JStorage"
    
    echo "☁️  Using Cloud Storage (Qdrant + Neo4j)"
    echo "📂 Working Dir: $WORKING_DIR"
    echo "🏷️  Workspace: $WORKSPACE"
    echo "🔗 Qdrant: ${QDRANT_URL:0:40}..."
    echo "🔗 Neo4j: ${NEO4J_URI:0:40}..."
else
    # Local mode
    echo "💾 Using Local Storage"
    export LIGHTRAG_VECTOR_STORAGE="NanoVectorDBStorage"
    export LIGHTRAG_GRAPH_STORAGE="NetworkXStorage"
fi

# =============================================================================
# BACKEND-SPECIFIC SETUP
# =============================================================================

if [ "$LLM_BACKEND" = "qwen" ]; then
    # QWEN via OpenRouter
    if [ -z "$OPENROUTER_API_KEY" ]; then
        echo "❌ OPENROUTER_API_KEY not set in .env"
        exit 1
    fi
    
    export OPENAI_API_KEY="$OPENROUTER_API_KEY"
    export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
    export OPENAI_API_BASE="https://openrouter.ai/api/v1"
    export LLM_BINDING_HOST="https://openrouter.ai/api/v1"
    export LLM_MODEL="qwen/qwen3-vl-8b-instruct"
    
    # Gemini embeddings configuration
    export EMBEDDING_MODEL="gemini-embedding-001"
    export EMBEDDING_DIM="1536"
    
    echo "🚀 Starting LightRAG Server with QWEN (via OpenRouter)..."
    echo "🤖 LLM Model: qwen/qwen3-vl-8b-instruct"
    echo "📐 Embedding: Gemini (gemini-embedding-001)"
    echo "🔗 LLM Host: https://openrouter.ai/api/v1"
    
    # Run Server with OpenAI binding for LLM, Gemini for embeddings
    lightrag-server \
        --working-dir "$WORKING_DIR" \
        --workspace "$WORKSPACE" \
        --llm-binding openai \
        --embedding-binding gemini

elif [ "$LLM_BACKEND" = "gemini" ]; then
    # Gemini
    if [ -z "$GEMINI_API_KEY" ]; then
        echo "❌ GEMINI_API_KEY not set in .env"
        exit 1
    fi
    
    echo "🚀 Starting LightRAG Server with Gemini..."
    echo "🤖 LLM Model: gemini-2.5-flash"
    echo "📐 Embedding: gemini-embedding-001"
    
    # Run Server with Gemini binding
    lightrag-server \
        --working-dir "$WORKING_DIR" \
        --workspace "$WORKSPACE" \
        --llm-binding gemini \
        --embedding-binding gemini

else
    echo "❌ Unknown LLM_BACKEND: $LLM_BACKEND"
    echo "   Please set LLM_BACKEND to 'qwen' or 'gemini' in .env"
    exit 1
fi
