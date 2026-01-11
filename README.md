# Daedalus: Deep Research Agent with Context Engineering

**Building a biomedical research agent that doesn't lose its mind during long tasks.**

## The Problem: Context Drift

Current AI agents (ReAct, multi-agent teams) suffer from **context drift**—they forget important details, lose focus, and hallucinate as tasks get longer. This is particularly problematic for:

- Processing dozens of research papers
- Maintaining citation coherence across long documents
- Synthesizing findings from multiple sources
- Writing comprehensive research reports section-by-section

## Our Solution: Context Engineering

A deep agent using LangGraph that implements **four context engineering techniques**:

1. **WRITE**: Section-by-section report generation with reflection loops and external memory (todo tracking)
2. **SELECT**: Multi-modal information retrieval via RAG sub-agent, web search, or direct file reading
3. **COMPRESS**: Context management at 80% capacity through iterative writing and strategic reflection
4. **ISOLATE**: Heavy tasks delegated to sub-agents with fresh context to prevent pollution

Plus **LightRAG** (hybrid/local/global/naive graph modes) for structured biomedical knowledge retrieval, and **Tavily + Wikipedia** for real-time web search.

## Architecture

### Hierarchical ReAct Agent Pattern

```
Main Orchestrator (DeepSeek/Gemini)
├── Strategizes and plans (read_todos, write_todos, think_strategically)
├── Writes outputs directly (write_file, edit_file)
└── Delegates to Sub-Agents (context isolation):
    ├── internet_researcher: Web search specialist (Tavily)
    ├── biomedical_researcher: RAG knowledge base (LightRAG + Qdrant + Neo4j)
    ├── filesystem_reader: Read-only file operations
    └── script_executor: Python/Bash execution, data visualization
```

### Key Features

- **Scratchpad-Driven Execution**: External todo list as persistent memory across context resets
- **Context Isolation**: Sub-agents receive only task descriptions, no parent conversation history
- **LightRAG Integration**: Graph-based retrieval with 4 query modes (hybrid/local/global/naive)
- **PhD-Level Quality Standards**: Embedded in system prompts (citation coherence, quantitative rigor)
- **Agent Skills**: Progressive disclosure metacognitive frameworks (gap analysis, insight generation)
- **High Recursion Limit**: 50,000 steps for long-running research tasks

## What This Proves

Context engineering techniques (write, select, compress, isolate) improve **accuracy and coherence** in long-horizon biomedical research tasks compared to standard RAG and basic agents.

## Project Structure

```
react-agent/
├── src/agent_graph/          # Core agent implementation
│   ├── graph.py              # Main graph builder (create_react_agent)
│   ├── state.py              # DeepAgentState with todo tracking
│   ├── tools.py              # 23+ tools including task delegation
│   ├── prompts.py            # 658 lines of system prompts
│   └── lightrag_agent.py     # Standalone LightRAG agent
├── src/rag/                  # LightRAG integration
│   ├── config.py             # Cloud (Qdrant+Neo4j) or Local storage
│   ├── query.py              # Query modes with citation support
│   └── rag_search_tool.py    # LangChain tool wrapper
├── agent_skills/             # Metacognitive frameworks
│   ├── gap_analysis.md       # 5-dimensional gap identification
│   ├── insight_generation.md # Hypothesis synthesis
│   └── research_progression.md # Session continuity tracking
└── agent_workspace/          # Sandboxed output directory
```

## Technical Innovations

- **Task delegation tool** with context isolation via `Command` state updates
- **LightRAG knowledge graph** with entity/relationship search over biomedical papers
- **Bayesian plan evolution**: Todos adapt based on findings (confirm, evolve, prune, deepen)
- **Citation coherence workflow**: Single References section, numbered citations, complete URLs
- **Data visualization integration**: Matplotlib plots with publication-quality standards

---

_For complete technical documentation, see [project_architecture_documentation.md](./project_architecture_documentation.md)_
