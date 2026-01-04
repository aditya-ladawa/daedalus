"""
LangGraph Tool for LightRAG Knowledge Base Retrieval

Uses config.py for all configuration (Qdrant + Neo4j credentials).

Usage in your LangGraph deep agent:

    from lightrag_tool import create_lightrag_tools, shutdown_rag
    
    # Initialize (reads from config.py → environment variables)
    rag, tools = await create_lightrag_tools()
    
    # Add to your agent
    all_tools = [*tools, tavily_tool, ...]
    
    # On shutdown
    await shutdown_rag()
"""
import re
from typing import Optional, Literal
from dataclasses import dataclass

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from dotenv import load_dotenv

from lightrag import LightRAG, QueryParam

# Import from shared config - single source of truth
from .config import get_rag_instance, print_config

load_dotenv()


# =============================================================================
# GLOBAL STATE
# =============================================================================

_rag_instance: Optional[LightRAG] = None


async def initialize_rag(
    working_dir: str = None, 
    workspace: str = None,
    storage_mode: str = None,
    llm_backend: str = None
) -> LightRAG:
    """
    Initialize LightRAG instance using config.py settings.
    
    Args:
        working_dir: Override working directory
        workspace: Override workspace (thread_id for conversation isolation)
        storage_mode: Override storage mode (cloud/local)
        llm_backend: Override LLM backend (gemini/qwen)
    """
    global _rag_instance
    
    if _rag_instance is not None:
        return _rag_instance
    
    print_config()
    _rag_instance = await get_rag_instance(
        working_dir=working_dir, 
        workspace=workspace,
        storage_mode=storage_mode,
        llm_backend=llm_backend
    )
    return _rag_instance


async def shutdown_rag():
    """Cleanup RAG connections."""
    global _rag_instance
    if _rag_instance:
        await _rag_instance.finalize_storages()
        _rag_instance = None
        print("🔌 LightRAG connections closed")


def get_rag() -> LightRAG:
    """Get initialized RAG instance."""
    if _rag_instance is None:
        raise RuntimeError("RAG not initialized. Call initialize_rag() first.")
    return _rag_instance


# =============================================================================
# TOOL SCHEMA
# =============================================================================

class SearchPapersInput(BaseModel):
    """Input schema for search_research_papers tool."""
    
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
    context_only: bool = Field(
        default=False,
        description="If True, return only raw context without LLM answer (faster, no API cost)"
    )


@dataclass
class Source:
    """A source reference from a retrieved chunk."""
    paper_name: str
    chunk_id: str
    excerpt: str
    paper_id: str = ""
    
    def __post_init__(self):
        match = re.search(r'processed_(\d+)', self.paper_name)
        if match:
            self.paper_id = match.group(1)


# =============================================================================
# CORE RETRIEVAL
# =============================================================================

async def search_knowledge_base(
    query: str,
    mode: str = "hybrid",
    top_k: int = 60,
    rag: LightRAG = None,
    context_only: bool = False,
) -> str:
    """
    Search the knowledge base and return answer with sources.
    
    Args:
        query: Research question
        mode: Search mode (hybrid, local, global, naive)
        top_k: Number of results to retrieve
        rag: LightRAG instance (uses global if None)
        context_only: If True, return raw context without LLM answer
    
    Returns:
        Answer string with formatted source citations (or raw context if context_only=True)
    """
    if rag is None:
        rag = get_rag()
    
    # Step 1: Get raw context to extract sources
    context = await rag.aquery(
        query,
        param=QueryParam(
            mode=mode,
            top_k=top_k,
            only_need_context=True,
            enable_rerank=False
        )
    )
    
    # If context_only, return immediately
    if context_only:
        return context
    
    sources = _parse_sources(context)
    
    # Step 2: Get LLM answer with citation guidance
    citation_prompt = None
    if sources:
        source_list = "\n".join([
            f"[{i}] {src.paper_name}" 
            for i, src in enumerate(sources, 1)
        ])
        citation_prompt = f"""
Cite sources using [N] format after claims.
Include citations for statistics (OR, CI, p-values).

Sources:
{source_list}
"""
    
    answer = await rag.aquery(
        query,
        param=QueryParam(
            mode=mode,
            top_k=top_k,
            user_prompt=citation_prompt,
            enable_rerank=False
        )
    )
    
    # Format output with references
    output = answer
    if sources:
        output += "\n\n**References:**\n"
        for i, src in enumerate(sources, 1):
            label = f"Paper {src.paper_id}" if src.paper_id else src.paper_name
            excerpt = src.excerpt[:80].replace("\n", " ")
            output += f"[{i}] {label} - \"{excerpt}...\"\n"
    
    return output


def _parse_sources(context: str) -> list[Source]:
    """Extract source references from LightRAG context."""
    if not context:
        return []
    
    sources = []
    seen = set()
    
    # Pattern for processed_*.md files
    for match in re.finditer(r'processed_\d+[^\s,\n"\'<>]*\.md', context):
        file_path = match.group(0)
        if file_path not in seen:
            seen.add(file_path)
            
            # Get excerpt and chunk ID near this reference
            start = max(0, match.start() - 50)
            end = min(len(context), match.start() + 300)
            excerpt = context[start:end].replace("\n", " ").strip()
            
            chunk_match = re.search(
                r'chunk-[a-f0-9]+', 
                context[max(0, match.start()-500):match.start()+500]
            )
            chunk_id = chunk_match.group(0) if chunk_match else "unknown"
            
            sources.append(Source(
                paper_name=file_path,
                chunk_id=chunk_id,
                excerpt=excerpt
            ))
    
    return sources


# =============================================================================
# LANGGRAPH TOOL
# =============================================================================

def create_lightrag_tool(rag: LightRAG = None) -> StructuredTool:
    """
    Create a LangGraph-compatible retrieval tool.
    
    Args:
        rag: LightRAG instance. If None, uses global instance.
    
    Returns:
        StructuredTool for use in LangGraph agents
    """
    
    async def _tool_func(query: str, mode: str = "hybrid", context_only: bool = False) -> str:
        return await search_knowledge_base(
            query=query,
            mode=mode,
            rag=rag,
            context_only=context_only
        )
    
    return StructuredTool.from_function(
        coroutine=_tool_func,
        name="search_research_papers",
        description=(
            "Search the biomedical research knowledge base. "
            "Use for: sleep disorders, psychiatric conditions, Mendelian randomization studies, "
            "statistical evidence (OR, CI, p-values), causal relationships. "
            "Returns answers with source citations [1], [2], etc."
        ),
        args_schema=SearchPapersInput,
    )


async def create_lightrag_tools(
    working_dir: str = None,
    workspace: str = None,
    storage_mode: str = None,
    llm_backend: str = None,
) -> tuple[LightRAG, list[StructuredTool]]:
    """
    Initialize RAG and create tools in one call.
    
    Args:
        working_dir: Override working directory
        workspace: Override workspace (thread_id for conversation isolation)
        storage_mode: Override storage mode (cloud/local)
        llm_backend: Override LLM backend (gemini/qwen)
    
    Usage:
        rag, tools = await create_lightrag_tools(
            workspace="thread_123",
            storage_mode="cloud",
            llm_backend="qwen"
        )
        all_tools = [*tools, tavily_tool, ...]
    
    Returns:
        (rag_instance, [search_tool])
    """
    rag = await initialize_rag(working_dir, workspace, storage_mode, llm_backend)
    tool = create_lightrag_tool(rag)
    return rag, [tool]


# =============================================================================
# CLI TEST
# =============================================================================

async def main():
    """Test the tool."""
    rag, tools = await create_lightrag_tools()
    
    search_tool = tools[0]
    result = await search_tool.ainvoke({
        "query": "What is the odds ratio between insomnia and ADHD?",
        "mode": "hybrid"
    })
    
    print("=" * 60)
    print("RESULT:")
    print("=" * 60)
    print(result)
    
    await shutdown_rag()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())