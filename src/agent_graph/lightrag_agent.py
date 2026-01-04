"""LightRAG Agent using create_react_agent with Google Gemini.

This module integrates LightRAG research paper search with LangGraph
using the create_react_agent pattern and Gemini models.

Exposes a 'graph' that can be selected in LangGraph Studio UI.
"""

import asyncio
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.runtime import Runtime

# Import RAG utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.rag_search_tool import search_research_papers
from agent_graph.context import Context
from agent_graph.utils import load_chat_model


# =============================================================================
# GRAPH BUILDER
# =============================================================================

def _build_lightrag_graph():
    """Build the LightRAG research agent graph.
    
    This creates a simple ReAct agent with access to the LightRAG knowledge base.
    Models are configured via Context and can be changed in LangGraph Studio.
    
    Returns:
        Compiled LangGraph agent ready for execution
    """
    # Use default context for initialization
    # Runtime context will be injected via Runtime[Context]
    ctx = Context()

    # Load default model (will be overridden at runtime)
    model = load_chat_model(ctx.subagent_model)

    # System prompt for the agent
    system_prompt = """You are an expert biomedical research assistant with access to a knowledge base of research papers on sleep disorders, psychiatric conditions, and Mendelian randomization studies.

## YOUR TOOL: `search_research_papers`

This tool queries a knowledge graph built from research papers. It returns raw context containing entities, relationships, and text chunks that you MUST use to answer questions.

## SEARCH MODES - Choose Wisely

| Mode | When to Use | Example Queries |
|------|-------------|-----------------|
| `hybrid` | DEFAULT - Start here for most questions | "relationship between insomnia and depression" |
| `local` | Specific facts, statistics, numbers | "What is the odds ratio for insomnia and ADHD?" |
| `global` | Broad themes, summaries, overviews | "What are the main findings across all papers?" |
| `naive` | Simple keyword matching | "papers mentioning bipolar disorder" |

## RESEARCH STRATEGY - Be Thorough

1. **Start broad, then narrow down:**
   - First query with `hybrid` mode to understand the landscape
   - If you need specific statistics → follow up with `local` mode
   - If you need overarching themes → use `global` mode

2. **Multiple queries are encouraged:**
   - Don't settle for one search if context is insufficient
   - Rephrase your query if results aren't relevant
   - Try different modes for the same topic

3. **Query formulation tips:**
   - Use specific medical/scientific terms
   - Include key entities: diseases, genes, study types
   - Ask focused questions rather than broad ones

## ANSWERING GUIDELINES

1. **Always cite sources:** Use paper names or chunk references from the context
   - Example: "According to the sleep disturbance study [processed_1.md]..."

2. **Be precise with statistics:**
   - Quote exact values: OR, CI, p-values, sample sizes
   - Include confidence intervals when available
   - Note the direction of effects (increased/decreased risk)

3. **Acknowledge limitations:**
   - If context is insufficient, say so clearly
   - Don't hallucinate facts not in the retrieved context
   - Distinguish between strong evidence and preliminary findings

4. **Structure your response:**
   - Lead with the direct answer
   - Support with evidence from the papers
   - Note any caveats or conflicting findings


Remember: You are a research assistant. Be thorough, accurate, and evidence-based."""
    
    print("🔬 Building LightRAG Research Agent...")
    print(f"   Model: {ctx.model} (configurable via Studio)")
    print("   Tool: search_research_papers")

    # Create the agent with RAG tool
    graph = create_react_agent(
        model,
        tools=[search_research_papers],
        prompt=system_prompt
    )
    
    print("✅ LightRAG Agent ready!")
    return graph


# Build and expose the graph for LangGraph Studio
graph = _build_lightrag_graph()

__all__ = ["graph"]


# =============================================================================
# RUNTIME EXAMPLE (for testing)
# =============================================================================

async def main():
    """Test the LightRAG agent."""
    print("🧠 LightRAG Agent initialized")
    print("   RAG Backend: Cloud (Qdrant + Neo4j)")
    print()

    # Test query
    query = "What does the sleep disturbance and psychiatric disorders paper talk about?"
    print(f"❓ Query: {query}\n")

    response = await graph.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })

    print("💬 Agent Response:")
    print(response["messages"])


if __name__ == "__main__":
    asyncio.run(main())
