"""
Query Script for LightRAG with Citation Support

Features:
- Standard querying with multiple modes
- Citation-aware querying (returns sources with chunks)
- Context-only mode for debugging
- Interactive CLI
"""
import asyncio
import time
import re
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv
from lightrag import QueryParam

from config import get_rag_instance, print_config, STORAGE_MODE

load_dotenv()


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SourceReference:
    """A reference to a source document chunk."""
    file_path: str
    chunk_id: str
    content: str
    excerpt: str = ""  # Short excerpt for display
    
    def __post_init__(self):
        # Generate excerpt if not provided
        if not self.excerpt and self.content:
            self.excerpt = self.content[:200].replace("\n", " ").strip()
            if len(self.content) > 200:
                self.excerpt += "..."


@dataclass 
class QueryResult:
    """Result from a query including answer and sources."""
    answer: str
    mode: str
    query_time: float
    sources: list[SourceReference] = field(default_factory=list)
    raw_context: Optional[str] = None


# =============================================================================
# QUERY FUNCTIONS
# =============================================================================

async def query(
    rag, 
    question: str, 
    mode: str = "hybrid",
    top_k: int = 60,
) -> QueryResult:
    """
    Standard query - returns LLM-generated answer.
    
    Args:
        rag: LightRAG instance
        question: Query string
        mode: Query mode (hybrid, local, global, naive, mix)
        top_k: Number of results to retrieve
    
    Returns:
        QueryResult with answer and timing
    """
    print(f"\n🔍 Querying ({mode}): {question[:80]}{'...' if len(question) > 80 else ''}")
    
    start = time.time()
    
    result = await rag.aquery(
        question, 
        param=QueryParam(mode=mode, top_k=top_k, enable_rerank=False)
    )
    
    elapsed = time.time() - start
    print(f"  ⏱️  Query time: {elapsed:.2f}s")
    
    return QueryResult(
        answer=result,
        mode=mode,
        query_time=elapsed
    )


async def query_with_context(
    rag,
    question: str,
    mode: str = "hybrid",
    top_k: int = 60,
) -> QueryResult:
    """
    Query and return raw context (for debugging/citation extraction).
    
    Uses only_need_context=True to get the raw retrieved chunks
    instead of an LLM-generated answer.
    """
    print(f"\n🔍 Getting context ({mode}): {question[:80]}...")
    
    start = time.time()
    
    context = await rag.aquery(
        question,
        param=QueryParam(
            mode=mode,
            top_k=top_k,
            only_need_context=True,  # Return raw context, not LLM answer
            enable_rerank=False
        )
    )
    
    elapsed = time.time() - start
    print(f"  ⏱️  Context retrieval: {elapsed:.2f}s")
    
    # Parse sources from context
    sources = parse_sources_from_context(context)
    
    return QueryResult(
        answer="",  # No LLM answer in context-only mode
        mode=mode,
        query_time=elapsed,
        sources=sources,
        raw_context=context
    )


async def query_with_citations(
    rag,
    question: str,
    mode: str = "hybrid",
    top_k: int = 60,
) -> QueryResult:
    """
    Query with citation support - returns answer AND extracted sources.
    
    This performs two queries:
    1. Get raw context to extract sources
    2. Get LLM answer with citation instructions
    """
    print(f"\n🔍 Querying with citations ({mode})...")
    
    start = time.time()
    
    # Step 1: Get context for source extraction
    context = await rag.aquery(
        question,
        param=QueryParam(
            mode=mode,
            top_k=top_k,
            only_need_context=True,
            enable_rerank=False
        )
    )
    
    sources = parse_sources_from_context(context)
    
    # Step 2: Get LLM answer with citation prompt
    citation_prompt = """
When answering, cite your sources using [^N] format where N is the source number.
Include a "Sources" section at the end listing the referenced documents.
Be specific about which source supports each claim.
"""
    
    answer = await rag.aquery(
        question,
        param=QueryParam(
            mode=mode,
            top_k=top_k,
            user_prompt=citation_prompt,
            enable_rerank=False
        )
    )
    
    elapsed = time.time() - start
    print(f"  ⏱️  Total query time: {elapsed:.2f}s")
    print(f"  📚 Sources found: {len(sources)}")
    
    return QueryResult(
        answer=answer,
        mode=mode,
        query_time=elapsed,
        sources=sources,
        raw_context=context
    )


def parse_sources_from_context(context: str) -> list[SourceReference]:
    """
    Parse source references from LightRAG raw context.
    
    The context format includes entities, relationships, and chunks
    with file_path information embedded.
    """
    sources = []
    
    if not context:
        return sources
    
    # Pattern 1: Look for file paths in the context
    # LightRAG includes file_path in entity/relationship metadata
    file_pattern = r'(?:file_path|source|from)[:\s]+["\']?([^"\'<>\n,]+\.md)["\']?'
    
    # Pattern 2: Look for chunk references
    chunk_pattern = r'chunk[-_]([a-f0-9]+)'
    
    # Extract unique file paths
    file_matches = re.findall(file_pattern, context, re.IGNORECASE)
    chunk_matches = re.findall(chunk_pattern, context, re.IGNORECASE)
    
    seen_files = set()
    
    for file_path in file_matches:
        if file_path not in seen_files:
            seen_files.add(file_path)
            
            # Try to extract content near this file reference
            excerpt = extract_excerpt_near_file(context, file_path)
            
            sources.append(SourceReference(
                file_path=file_path,
                chunk_id=f"chunk-{chunk_matches[0]}" if chunk_matches else "unknown",
                content=excerpt,
                excerpt=excerpt[:150] + "..." if len(excerpt) > 150 else excerpt
            ))
    
    # If no explicit file paths found, try to extract from structured sections
    if not sources:
        sources = extract_sources_from_sections(context)
    
    return sources


def extract_excerpt_near_file(context: str, file_path: str, window: int = 500) -> str:
    """Extract text content near a file path reference."""
    idx = context.lower().find(file_path.lower())
    if idx == -1:
        return ""
    
    start = max(0, idx - window // 2)
    end = min(len(context), idx + window // 2)
    
    return context[start:end].strip()


def extract_sources_from_sections(context: str) -> list[SourceReference]:
    """
    Extract sources from structured context sections.
    
    LightRAG context often has sections like:
    - Entities: ...
    - Relationships: ...
    - Sources: ...
    """
    sources = []
    
    # Look for source indicators
    source_indicators = [
        r'processed_\d+[^.\s]*\.md',  # processed_27_*.md pattern
        r'[A-Za-z0-9_-]+\.md',         # Any .md file
    ]
    
    for pattern in source_indicators:
        matches = re.findall(pattern, context)
        for match in matches:
            if match not in [s.file_path for s in sources]:
                sources.append(SourceReference(
                    file_path=match,
                    chunk_id="inferred",
                    content="",
                    excerpt="(extracted from context)"
                ))
    
    return sources


def format_sources_for_report(sources: list[SourceReference]) -> str:
    """Format sources as a references section for reports (papers with chunks)."""
    if not sources:
        return "\n## References\n\n_No sources identified._\n"
    
    # Filter to only include actual paper files (processed_*.md or *.md)
    # and deduplicate by file_path + chunk_id combination
    paper_sources = []
    seen = set()
    
    for src in sources:
        # Only include .md files (actual papers)
        if not src.file_path.endswith('.md'):
            continue
        
        # Create unique key from file + chunk
        key = f"{src.file_path}:{src.chunk_id}"
        if key not in seen:
            seen.add(key)
            paper_sources.append(src)
    
    if not paper_sources:
        return "\n## References\n\n_No paper sources identified._\n"
    
    lines = ["\n## References\n"]
    
    for i, src in enumerate(paper_sources, 1):
        lines.append(f"[{i}] **{src.file_path}**")
        if src.chunk_id != "unknown" and src.chunk_id != "inferred":
            lines.append(f"    - Chunk: `{src.chunk_id}`")
        if src.excerpt:
            lines.append(f"    - Excerpt: \"{src.excerpt}\"")
        lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# INTERACTIVE CLI
# =============================================================================

def print_help():
    """Print help message."""
    print("""
📖 LightRAG Query Commands:
    
    Query Modes:
    /hybrid <query>  - Combined local + global (default)
    /local <query>   - Entity-focused (specific relationships)
    /global <query>  - Theme-focused (broad patterns)
    /naive <query>   - Vector-only (no graph)
    
    Citation Mode:
    /cite <query>    - Query with citations [^1], [^2]
    /context <query> - Get raw context only (for debugging)
    
    Utilities:
    /status          - Show configuration
    /help            - Show this help
    exit, quit       - Exit
    
Examples:
    What is the OR between insomnia and ADHD?
    /cite What causes depression in the studies?
    /local What SNPs are associated with sleep disorders?
""")


async def interactive_mode(rag, storage_mode=None, workspace=None):
    """Run interactive query loop."""
    mode = storage_mode if storage_mode is not None else STORAGE_MODE
    ws = workspace if workspace is not None else WORKSPACE
    
    print("\n" + "="*60)
    print("💡 LightRAG Query Interface")
    print("="*60)
    print(f"  Storage: {'☁️  Cloud (Qdrant + Neo4j)' if mode == 'cloud' else '💾 Local'}")
    print(f"  Workspace: {ws}")
    print("  Type '/help' for commands, 'exit' to quit")
    print("="*60)
    
    while True:
        try:
            q = input("\n🔍 Query: ").strip()
            
            if not q:
                continue
            
            if q.lower() in ["exit", "quit"]:
                break
            
            if q.lower() == "/help":
                print_help()
                continue
            
            if q.lower() == "/status":
                print_config(storage_mode=storage_mode, workspace=workspace)
                continue
            
            # Parse command
            mode = "hybrid"
            use_citations = False
            context_only = False
            
            if q.startswith("/"):
                parts = q.split(" ", 1)
                cmd = parts[0].lower()
                
                if cmd == "/cite":
                    use_citations = True
                    q = parts[1] if len(parts) > 1 else ""
                elif cmd == "/context":
                    context_only = True
                    q = parts[1] if len(parts) > 1 else ""
                elif cmd in ["/local", "/global", "/hybrid", "/naive", "/mix"]:
                    mode = cmd[1:]
                    q = parts[1] if len(parts) > 1 else ""
                else:
                    print(f"⚠️  Unknown command: {cmd}")
                    continue
                
                if not q:
                    print("⚠️  Please provide a query")
                    continue
            
            # Execute query
            if context_only:
                result = await query_with_context(rag, q, mode)
                print("\n" + "-"*60)
                print("📄 Raw Context:")
                print("-"*60)
                print(result.raw_context[:2000] if result.raw_context else "No context")
                if result.raw_context and len(result.raw_context) > 2000:
                    print(f"\n... ({len(result.raw_context) - 2000} more characters)")
                print("-"*60)
                
            elif use_citations:
                result = await query_with_citations(rag, q, mode)
                print("\n" + "-"*60)
                print("🤖 Answer:")
                print("-"*60)
                print(result.answer)
                print(format_sources_for_report(result.sources))
                
            else:
                result = await query(rag, q, mode)
                print("\n" + "-"*60)
                print("🤖 Answer:")
                print("-"*60)
                print(result.answer)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Query LightRAG")
    parser.add_argument("--db", "-d", default=None,
                        help="Working directory for LightRAG")
    parser.add_argument("--query", "-q", default=None,
                        help="Single query (non-interactive)")
    parser.add_argument("--mode", "-m", default="hybrid",
                        choices=["hybrid", "local", "global", "naive", "mix"])
    parser.add_argument("--cite", action="store_true",
                        help="Enable citation mode")
    parser.add_argument("--workspace", "-w", default=None,
                        help="Workspace (thread_id) for data isolation")
    parser.add_argument("--storage", "-s", default=None,
                        choices=["cloud", "local"],
                        help="Storage mode to use (overrides config.py)")
    parser.add_argument("--llm-backend", "-l", default=None,
                        choices=["gemini", "qwen"],
                        help="LLM backend to use (overrides config.py)")
    
    args = parser.parse_args()
    
    rag = await get_rag_instance(
        working_dir=args.db, 
        workspace=args.workspace,
        storage_mode=args.storage,
        llm_backend=args.llm_backend
    )
    
    try:
        if args.query:
            # Single query mode
            if args.context:
                result = await query_with_context(rag, args.query, args.mode)
                print(result.raw_context)
            elif args.cite:
                result = await query_with_citations(rag, args.query, args.mode)
                print(result.answer)
                print(format_sources_for_report(result.sources))
            else:
                result = await query(rag, args.query, args.mode)
                print(result.answer)
        else:
            # Interactive mode
            await interactive_mode(rag, storage_mode=args.storage, workspace=args.workspace)
    
    finally:
        await rag.finalize_storages()
        print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())