"""
Shared Configuration for LightRAG with Gemini
"""
import os
import numpy as np
from pathlib import Path
from lightrag import LightRAG
from lightrag.utils import setup_logger, wrap_embedding_func_with_attrs
from lightrag.llm.gemini import gemini_model_complete
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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Models
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
    """Gemini LLM function with minimal thinking config."""
    # Configure minimal thinking for Gemini 3 Flash (faster, lower cost)
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
    """Gemini embedding function."""
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
