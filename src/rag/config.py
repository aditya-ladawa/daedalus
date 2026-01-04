"""
LightRAG Configuration

Storage Mode: Set STORAGE_MODE to "cloud" or "local"
Workspace: Each conversation/project should have its own WORKSPACE for data isolation
"""
import os
import asyncio
import numpy as np
from pathlib import Path
from lightrag import LightRAG
from lightrag.utils import setup_logger, wrap_embedding_func_with_attrs
from lightrag.llm.gemini import gemini_model_complete
from lightrag.llm.openai import openai_complete_if_cache
from google import genai
from google.genai import types

from dotenv import load_dotenv
load_dotenv()

# Setup logger
setup_logger("lightrag", level="INFO")

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================

# Storage mode: "cloud" or "local" (user must explicitly choose)
STORAGE_MODE = "cloud"

# Working directory (always needed for KV cache)
WORKING_DIR = "./lightrag_data_local"

# Workspace for data isolation
# IMPORTANT: Each conversation/project should have a unique workspace
# This isolates embeddings and graph data per project
WORKSPACE = "default"

# =============================================================================
# LLM CONFIGURATION
# =============================================================================

# Backend: "gemini" or "qwen" (via OpenRouter)
LLM_BACKEND = "gemini"

# Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"  # Using stable version
# QWEN/OpenRouter
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
QWEN_MODEL = "qwen/qwen3-vl-32b-instruct"

# Model selection
LLM_MODEL = QWEN_MODEL if LLM_BACKEND == "qwen" else GEMINI_MODEL

# Embedding (always Gemini)
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 1536

# =============================================================================
# CLOUD STORAGE CREDENTIALS (only used when STORAGE_MODE="cloud")
# =============================================================================

# Qdrant Cloud
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")

# Neo4j Aura
NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

# =============================================================================
# LLM & EMBEDDING FUNCTIONS
# =============================================================================

_genai_client = None


def get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
    return _genai_client


def create_llm_func(backend: str):
    """Create LLM function for the specified backend."""
    async def llm_func_impl(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
        if backend == "qwen":
            return await openai_complete_if_cache(
                model=QWEN_MODEL,
                prompt=prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_BASE_URL,
                **kwargs
            )
        else:  # gemini
            thinking_config = types.ThinkingConfig(thinking_level="minimal")
            gen_config = types.GenerateContentConfig(thinking_config=thinking_config)
            return await gemini_model_complete(
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=GEMINI_API_KEY,
                model_name=GEMINI_MODEL,
                config=gen_config,
                **kwargs
            )
    return llm_func_impl


# Default LLM function (for backward compatibility)
async def llm_func(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
    """LLM function supporting both Gemini and QWEN (uses global LLM_BACKEND)."""
    return await create_llm_func(LLM_BACKEND)(prompt, system_prompt, history_messages, **kwargs)


@wrap_embedding_func_with_attrs(
    embedding_dim=EMBEDDING_DIM,
    max_token_size=2048,
    model_name=EMBEDDING_MODEL
)
async def embedding_func(texts: list[str]) -> np.ndarray:
    """Embedding function using Gemini."""
    client = get_genai_client()
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIM
        )
    )
    embeddings = []
    for emb in result.embeddings:
        vec = np.array(emb.values)
        vec = vec / np.linalg.norm(vec)
        embeddings.append(vec)
    return np.array(embeddings)


# =============================================================================
# RAG INSTANCE FACTORY
# =============================================================================

def _get_cloud_config() -> dict:
    """Get cloud storage configuration (Qdrant + Neo4j)."""
    if not QDRANT_URL or not NEO4J_URI:
        raise ValueError(
            "Cloud storage requires QDRANT_URL and NEO4J_URI. "
            "Set these in .env or switch to STORAGE_MODE=local"
        )
    
    # LightRAG reads connection details from environment variables
    # We only need to specify the storage class names
    return {
        # Vector storage: Qdrant Cloud
        "vector_storage": "QdrantVectorDBStorage",
        # Graph storage: Neo4j Aura
        "graph_storage": "Neo4JStorage",
    }


def _get_local_config() -> dict:
    """Get local storage configuration (NanoVectorDB + NetworkX)."""
    # LightRAG uses these by default, no extra config needed
    return {}


async def get_rag_instance(
    working_dir: str = None,
    workspace: str = None,
    storage_mode: str = None,
    llm_backend: str = None,
) -> LightRAG:
    """
    Initialize and return a LightRAG instance.
    
    Args:
        working_dir: Override WORKING_DIR from env
        workspace: Override WORKSPACE from env (for conversation isolation)
        storage_mode: Override STORAGE_MODE ("cloud" or "local")
        llm_backend: Override LLM_BACKEND ("gemini" or "qwen")
    
    Returns:
        Configured LightRAG instance
    """
    target_dir = working_dir if working_dir is not None else WORKING_DIR
    target_workspace = workspace if workspace is not None else WORKSPACE
    mode = storage_mode if storage_mode is not None else STORAGE_MODE
    backend = llm_backend if llm_backend is not None else LLM_BACKEND
    
    # Select model and LLM function based on backend
    model = QWEN_MODEL if backend == "qwen" else GEMINI_MODEL
    llm_function = create_llm_func(backend)
    
    # Ensure working directory exists (non-blocking)
    await asyncio.to_thread(lambda: Path(target_dir).mkdir(parents=True, exist_ok=True))
    
    # Base configuration
    config = {
        "working_dir": target_dir,
        "workspace": target_workspace,
        "llm_model_func": llm_function,
        "llm_model_name": model,
        "embedding_func": embedding_func,
    }
    
    # Add storage-specific config based on mode
    if mode == "cloud":
        print(f"☁️  Storage: Cloud (Qdrant + Neo4j)")
        config.update(_get_cloud_config())
    elif mode == "local":
        print(f"💾 Storage: Local (NanoVectorDB + NetworkX)")
        config.update(_get_local_config())
    else:
        raise ValueError(f"Invalid STORAGE_MODE: {mode}. Must be 'cloud' or 'local'")
    
    print(f"📂 Working Dir: {target_dir}")
    print(f"🏷️  Workspace: {target_workspace}")
    
    # Initialize LightRAG in a thread because it performs blocking IO (tiktoken loading)
    rag = await asyncio.to_thread(LightRAG, **config)

    # Initialize storages
    # Note: LightRAG uses sync QdrantClient which makes blocking calls.
    # BG_JOB_ISOLATED_LOOPS=true in .env handles this for LangGraph deployment
    await rag.initialize_storages()

    print("✅ LightRAG ready")
    return rag


# =============================================================================
# UTILITIES
# =============================================================================

def print_config(storage_mode=None, workspace=None):
    """Print current configuration."""
    mode = storage_mode if storage_mode is not None else STORAGE_MODE
    ws = workspace if workspace is not None else WORKSPACE
    print("\n" + "="*50)
    print("⚙️  LightRAG Configuration")
    print("="*50)
    print(f"  Storage Mode:    {mode}")
    print(f"  Workspace:       {ws}")
    print(f"  Working Dir:     {WORKING_DIR}")
    print(f"  LLM Backend:     {LLM_BACKEND}")
    print(f"  LLM Model:       {LLM_MODEL}")
    print(f"  Embedding:       {EMBEDDING_MODEL} ({EMBEDDING_DIM}d)")
    if mode == "cloud":
        print(f"  Qdrant URL:      {QDRANT_URL[:50]}..." if len(QDRANT_URL) > 50 else f"  Qdrant URL:      {QDRANT_URL}")
        print(f"  Neo4j URI:       {NEO4J_URI[:50]}..." if len(NEO4J_URI) > 50 else f"  Neo4j URI:       {NEO4J_URI}")
    print("="*50 + "\n")


if __name__ == "__main__":
    print_config()