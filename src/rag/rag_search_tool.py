"""
LightRAG search tool for LangGraph agents.

Uses @tool decorator from langchain_core for proper async handling.
RAG instance is cached globally and initialized on first use.

Usage:
    from rag.rag_search_tool import search_research_papers, shutdown_rag

    # Use in agent
    tools = [search_research_papers]

    # On shutdown (optional)
    await shutdown_rag()
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from lightrag import LightRAG, QueryParam

from .config import get_rag_instance, print_config

# Global RAG instance cache
_rag_cache: Optional[LightRAG] = None


async def get_cached_rag() -> LightRAG:
    """Get or initialize cached RAG instance."""
    global _rag_cache

    if _rag_cache is None:
        print_config()
        _rag_cache = await get_rag_instance()

    return _rag_cache


async def shutdown_rag():
    """Cleanup RAG connections."""
    global _rag_cache
    if _rag_cache:
        await _rag_cache.finalize_storages()
        _rag_cache = None
        print("🔌 LightRAG connections closed")


class SearchInput(BaseModel):
    """Input schema for RAG search tool."""

    query: str = Field(
        description="Research question to answer from the biomedical knowledge base"
    )
    mode: Literal["hybrid", "local", "global", "naive"] = Field(
        default="hybrid",
        description=(
            "Search mode: "
            "'hybrid' (default) - combined entity + relationship search; "
            "'local' - for specific facts like OR, CI, p-values; "
            "'global' - for broad patterns across papers; "
            "'naive' - simple vector similarity"
        )
    )


@tool(args_schema=SearchInput)
async def search_research_papers(query: str, mode: str = "hybrid") -> str:
    """Search the biomedical research knowledge base built from research papers.

    Returns raw context containing entities, relationships, and text chunks with source references.
    You can call this tool multiple times with different queries/modes to gather sufficient context.

    Topics covered:
    - Sleep disorders (insomnia, hypersomnia, sleep apnea)
    - Psychiatric conditions (depression, anxiety, ADHD, bipolar, schizophrenia)
    - Mendelian randomization studies and causal inference
    - Genetic associations, odds ratios, confidence intervals

    Search modes:
    - hybrid (default): Best for most queries - combines entity and relationship search
    - local: Best for specific statistics (OR, CI, p-values, sample sizes)
    - global: Best for broad themes and overarching patterns across papers
    - naive: Simple vector similarity search

    Tips for effective queries:
    - Use specific medical terms (e.g., "insomnia" not "sleep problems")
    - Include study type if relevant (e.g., "Mendelian randomization")
    - Ask focused questions for better results
    """
    # Get cached RAG instance (initialized once on first call)
    rag = await get_cached_rag()

    # Query the knowledge base
    context = await rag.aquery(
        query,
        param=QueryParam(
            mode=mode,
            top_k=30,           # KG Top K
            chunk_top_k=8,      # Chunk Top K
            only_need_context=True,
            enable_rerank=False
        )
    )

    return context
