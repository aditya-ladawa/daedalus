"""
Shared Configuration for LightRAG with Gemini and QWEN (OpenRouter)
"""
import os
import numpy as np
from pathlib import Path
from lightrag import LightRAG
from lightrag.utils import setup_logger, wrap_embedding_func_with_attrs
from lightrag.llm.gemini import gemini_model_complete
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from google import genai
from google.genai import types

from dotenv import load_dotenv
load_dotenv()

# Setup logger
setup_logger("lightrag", level="INFO")

# =============================================================================
# CONFIG
# =============================================================================

# WORKING_DIR = "./lightrag_data"
WORKING_DIR = "./lightrag_data_2"

# Backend Selection: "gemini" or "qwen" (via OpenRouter)
LLM_BACKEND = os.getenv("LLM_BACKEND", "qwen")  # Default to gemini

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# QWEN/OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "n/a")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
QWEN_MODEL = "qwen/qwen3-vl-32b-instruct"

# Model configuration based on backend
if LLM_BACKEND == "qwen":
    LLM_MODEL = QWEN_MODEL
    # Use Gemini embeddings for both backends (user has access to Gemini embeddings)
    EMBEDDING_MODEL = "gemini-embedding-001"
    EMBEDDING_DIM = 1536
else:  # Default to Gemini
    LLM_MODEL = "gemini-3-flash-preview"
    EMBEDDING_MODEL = "gemini-embedding-001"
    EMBEDDING_DIM = 1536  # gemini-embedding-001 supports up to 3072, using 1536

# =============================================================================
# FUNCTIONS
# =============================================================================

_genai_client = None

def get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
    return _genai_client


async def llm_func(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
    """LLM function supporting both Gemini and QWEN (via OpenRouter)."""
    
    if LLM_BACKEND == "qwen":
        # Use OpenAI-compatible API for QWEN via OpenRouter
        return await openai_complete_if_cache(
            model=LLM_MODEL,
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            **kwargs
        )
    else:
        # Use Gemini with minimal thinking config
        thinking_config = types.ThinkingConfig(thinking_level="minimal")
        gen_config = types.GenerateContentConfig(thinking_config=thinking_config)

        return await gemini_model_complete(
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=GEMINI_API_KEY,
            model_name=LLM_MODEL,
            config=gen_config, 
            **kwargs
        )


@wrap_embedding_func_with_attrs(
    embedding_dim=EMBEDDING_DIM,
    max_token_size=2048,
    model_name=EMBEDDING_MODEL
)
async def embedding_func(texts: list[str]) -> np.ndarray:
    """Embedding function using Gemini embeddings for all backends."""
    # Always use Gemini embedding (user has access to Gemini embeddings)
    client = get_genai_client()
    
    # Call embed_content API
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIM
        )
    )
    
    # Extract and normalize
    embeddings = []
    for emb in result.embeddings:
        vec = np.array(emb.values)
        vec = vec / np.linalg.norm(vec)
        embeddings.append(vec)
    
    return np.array(embeddings)


async def get_rag_instance(working_dir: str = None) -> LightRAG:
    """Initialize and return a LightRAG instance pointing to working_dir (defaults to env var or constant)."""
    target_dir = working_dir or WORKING_DIR
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"🔄 Loading LightRAG from: {target_dir}")
    rag = LightRAG(
        working_dir=target_dir,
        llm_model_func=llm_func,
        llm_model_name=LLM_MODEL,
        embedding_func=embedding_func,
    )
    # Initialize storages (loads existing data or creates new)
    await rag.initialize_storages()
    print("✅ LightRAG loaded and ready.")
    return rag


def export_config_for_shell():
    """Export configuration as shell environment variables for run_server.sh to source."""
    print(f"export LLM_BACKEND={LLM_BACKEND}")
    print(f"export LLM_MODEL={LLM_MODEL}")
    print(f"export EMBEDDING_MODEL={EMBEDDING_MODEL}")
    print(f"export OPENROUTER_BASE_URL={OPENROUTER_BASE_URL}")
    print(f"export OPENROUTER_API_KEY={OPENROUTER_API_KEY}")
    print(f"export GEMINI_API_KEY={GEMINI_API_KEY}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--export-shell":
        export_config_for_shell()
