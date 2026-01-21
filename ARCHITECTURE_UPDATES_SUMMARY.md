# Architecture Updates Summary

## Overview

This document summarizes the major architectural changes made to the Daedalus Deep Research Agent to implement an **Anthropic-style 5-phase iterative research workflow** with parallel tool execution capabilities.

---

## Key Changes Implemented

### 1. **Parallel Tool Calls Enabled** ✅

**File**: `src/agent_graph/graph.py`

**Change**: Modified `parallel_tool_calls` from `False` to `True`

**Impact**: The main agent can now spawn **multiple subagents simultaneously** during research phases, enabling true parallel research across different aspects of a query.

```python
# Before
main_model.bind(parallel_tool_calls=False)

# After
main_model.bind(parallel_tool_calls=True)
```

---

### 2. **Anthropic 5-Phase Iterative Research Loop** ✅

**File**: `src/agent_graph/prompts.py`

**Change**: Replaced the previous workflow with a structured 5-phase loop:

1. **PLAN & RECONNAISSANCE**: Assess complexity, parallel recon (RAG + Internet), create todos
2. **PARALLEL RESEARCH**: Spawn multiple subagents across todos or aspects
3. **SYNTHESIZE & EVALUATE**: Receive results, use `think_strategically`, update todos
4. **DECISION POINT**: Check for gaps, loop back if needed
5. **PROGRESSIVE WRITING**: Write section-by-section, fill placeholders, quality checks

**Key Features**:

- **Strategy A (Breadth)**: One subagent per todo (if independent)
- **Strategy B (Depth)**: Multiple subagents per complex todo
- **Hybrid**: Mix of both strategies based on task needs

---

### 3. **Progressive Writing Strategy (Skeleton + Fill)** ✅

**Files**:

- `src/benchmarking_stuff/agents/prompts_deep_agent.py`
- `src/benchmarking_stuff/agents/prompts_basic_agent.py`
- `src/benchmarking_stuff/agents/basic_agent.py` (added `edit_report` tool)

**Change**: Implemented a "Skeleton + Fill" approach to prevent the "lazy LLM" problem:

1. Create skeleton report with placeholders: `[PLACEHOLDER: Section Name]`
2. Iteratively fill each section using `edit_file` or `edit_report`
3. Perform final quality checks to remove all placeholders
4. Verify citations are complete

**Impact**: Forces step-by-step completion and avoids context limits for long reports.

---

### 4. **Centralized Report Storage** ✅

**Files Updated**:

- `src/benchmarking_stuff/agents/basic_agent.py`
- `src/benchmarking_stuff/agents/deep_agent.py`
- `src/benchmarking_stuff/rigorous_bench/evaluate_deep_agent.py`
- `src/benchmarking_stuff/rigorous_bench/evaluate_basic_agent.py`
- `src/benchmarking_stuff/deep_research_bench/run_agent.py`

**New Structure**:

```
src/benchmarking_stuff/eval_reports/
├── deep_research_bench/
│   ├── deep_agent/
│   │   ├── gemini-2.0-flash-exp_report_v1.md
│   │   └── ...
│   └── basic_agent/
│       ├── gemini-2.0-flash-exp_report_v1.md
│       └── ...
└── rigorous_bench/
    ├── deep_agent/
    │   ├── gemini-2.0-flash-exp_report_v1.md
    │   └── ...
    └── basic_agent/
        ├── gemini-2.0-flash-exp_report_v1.md
        └── ...
```

**Impact**: All benchmark reports are now in a single, organized location for easier analysis.

---

### 5. **Prompt Cleanup** ✅

**File**: `src/agent_graph/prompts.py`

**Changes**:

- Removed redundant "CORE WORKFLOW" section (superseded by 5-phase loop)
- Removed duplicate "Citation Coherence Rules" section
- Removed orphaned "ITERATIVE WRITING PROCESS" section
- Fixed typos: `agent_workspawce` → `agent_workspace`
- Removed orphaned "w" characters

**Impact**: Single source of truth for workflow instructions, improved clarity.

---

### 6. **Subagent Tooling Enhancement** ✅

**Files**: `src/agent_graph/prompts.py` (subagent prompts)

**Change**: Ensured all subagents have access to `think_strategically` tool to assess research needs before executing.

**Subagents**:

- `internet_researcher`
- `biomedical_researcher`
- `script_executor`
- `filesystem_reader`

**Impact**: Subagents can now make informed decisions about research depth and approach.

---

### 7. **Documentation Updates** ✅

**File**: `project_architecture_documentation.md`

**Changes**:

1. Updated directory structure to reflect centralized `eval_reports/`
2. Added comprehensive "Benchmarking Architectures" section (lines 586-836) with:
   - Agent graph diagrams for all 4 benchmarks
   - Detailed workflow explanations
   - Metrics and evaluation criteria
3. Updated "Runtime Configuration" to reflect parallel tool calls enabled
4. Updated "Key Design Decisions" table to reflect parallel subagent execution

---

## Benchmarking Architecture

### Four Benchmarks Implemented

1. **Deep Research Bench + Deep Agent**: Full 5-phase workflow with parallel research
2. **Deep Research Bench + Basic Agent**: Simple ReAct loop with progressive writing
3. **RigorousBench + Deep Agent**: 5-phase workflow on standardized questions
4. **RigorousBench + Basic Agent**: Simple ReAct on standardized questions

### Evaluation Metrics

#### Deep Research Bench (Custom)

- **DeepEval Metrics**: Faithfulness, Relevancy, Contextual Precision, Contextual Recall
- **Custom Metrics**: Scientific Precision, Citation Quality, Structural Coherence
- **FACT Evaluation**: Citation verification via web scraping (Jina AI Reader)

#### RigorousBench (Standardized)

- **RACE Score**: Relevance, Accuracy, Completeness, Efficiency
- **Ragas Metrics**: Faithfulness, Answer Relevance, Context Precision, Context Recall

---

## Known Issues & Next Steps

### Blockers

1. **FACT Evaluation Errors**: Jina AI Reader encountering 503/524 errors during URL scraping
2. **Basic Agent Progressive Writing**: Struggles with Skeleton + Fill, leaves placeholders unfilled
3. **Deep Agent RACE Scores**: Low scores (~0.40) likely due to leftover placeholders and repetition

### Recommended Next Steps

1. **Strengthen Final Quality Checks**: Add aggressive placeholder removal enforcement
2. **Add Report Length Limits**: Cap at 8,000 words to improve focus and reduce repetition
3. **Simplify Basic Agent Writing**: Revert to append strategy or add robust loop mechanism
4. **Alternative Scraping**: Consider alternatives to Jina AI if issues persist
5. **Benchmark Reruns**: Test with refined prompts and configurations

---

## Environment Variables Required

```bash
GEMINI_API_KEY          # For Gemini models
GOOGLE_API_KEY          # Alternative for Gemini
DEEPSEEK_API_KEY        # For DeepSeek models
TAVILY_API_KEY          # For web search
OPENAI_API_KEY          # For OpenAI models (if used)
```

---

## File Reference Summary

### Core Agent Files

- `src/agent_graph/graph.py` - Main graph builder (parallel_tool_calls=True)
- `src/agent_graph/prompts.py` - 5-phase workflow prompts
- `src/agent_graph/state.py` - Agent state with todo tracking
- `src/agent_graph/tools.py` - 23+ tools including task delegation

### Benchmark Agent Files

- `src/benchmarking_stuff/agents/deep_agent.py` - Deep agent implementation
- `src/benchmarking_stuff/agents/basic_agent.py` - Basic agent implementation
- `src/benchmarking_stuff/agents/prompts_deep_agent.py` - Deep agent prompts
- `src/benchmarking_stuff/agents/prompts_basic_agent.py` - Basic agent prompts

### Evaluation Files

- `src/benchmarking_stuff/deep_research_bench/run_agent.py` - Deep Research Bench runner
- `src/benchmarking_stuff/rigorous_bench/evaluate_deep_agent.py` - RigorousBench Deep Agent eval
- `src/benchmarking_stuff/rigorous_bench/evaluate_basic_agent.py` - RigorousBench Basic Agent eval

### Report Storage

- `src/benchmarking_stuff/eval_reports/` - Centralized report directory

---

## Design Philosophy

### Anthropic Pattern Implementation

The agent now follows Anthropic's research best practices:

1. **Parallel Research**: Multiple subagents execute simultaneously during research phases
2. **Iterative Refinement**: Continuous loop of research → synthesis → decision → writing
3. **Strategic Thinking**: `think_strategically` used at key decision points
4. **Progressive Writing**: Section-by-section construction prevents context overflow
5. **Quality Gates**: Final checks ensure completeness and citation accuracy

### Context Engineering Techniques

1. **WRITE**: Section-by-section with reflection loops and external memory
2. **SELECT**: Multi-modal retrieval (RAG, web, files)
3. **COMPRESS**: Context management at 80% capacity
4. **ISOLATE**: Heavy tasks delegated to fresh-context subagents

---

## Performance Characteristics

### Main Agent

- Model: `deepseek/deepseek-chat` (or configurable)
- Max Tokens: 16,384
- Temperature: 0.3
- Recursion Limit: 50,000 steps
- **Parallel Tool Calls: Enabled**

### Subagents

- Model: `google_genai/gemini-2.5-flash` (or configurable)
- Temperature: 0.0 (deterministic)
- Context: Isolated (no parent history)
- Tools: Specialized per subagent type

---

## Conclusion

The Daedalus agent now implements a state-of-the-art research workflow that combines:

- **Parallel execution** for efficiency
- **Iterative refinement** for quality
- **Progressive writing** for long-form outputs
- **Context engineering** for coherence

All changes have been documented, tested, and integrated into the benchmarking framework.

---

_Last Updated: 2026-01-20_
_Architecture Version: 2.0 (Anthropic Pattern)_
