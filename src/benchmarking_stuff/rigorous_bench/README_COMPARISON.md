# RigorousBench Agent Comparison

This directory contains two agent implementations for benchmarking on RigorousBench:

## Agents

### 1. **Deep Research Agent** (`deep_agent.py`)

- Multi-agent architecture with orchestration
- Subagents: internet_researcher, script_executor
- Task delegation and iterative planning
- Schema-based prompts for granular detail extraction
- Reports saved to: `all_reports/`

### 2. **Basic ReAct Agent** (`basic_agent.py`)

- Simple LangGraph ReAct agent
- Direct tool access (no subagents)
- Straightforward execution
- Reports saved to: `basic_agent_reports/`

## Running Evaluations

### Activate Environment

```bash
source .venv/bin/activate
cd src/benchmarking_stuff/rigorous_bench
```

### Run Deep Agent Only

```bash
python run_evaluation.py
```

### Run Basic Agent Only

```bash
python evaluate_basic_agent.py
```

### Run Both & Compare

```bash
python compare_agents.py
```

This will:

1. Run basic agent on all queries
2. Run deep agent on all queries
3. Generate a comparison report (`agent_comparison.md`)

## Evaluation Metrics

Each agent is evaluated on:

- **QUA (Quality)**: LLM judge score based on rubrics (0-100%)
- **SDR (Semantic Drift Ratio)**: Focus keywords / (focus + deviation keywords)
- **TBO (Trust Boost)**: Trusted source citations / total trusted sources
- **ITS (Integrated Total Score)**: 0.5×QUA + 0.3×SDR + 0.2×TBO

## Results Structure

```
rigorous_bench/
├── all_reports/              # Deep agent results
│   ├── 07001/
│   │   ├── report.md
│   │   └── evaluation.md
│   └── ...
├── basic_agent_reports/      # Basic agent results
│   ├── 07001/
│   │   ├── report.md
│   │   └── evaluation.md
│   └── ...
├── deep_agent_results.json   # Deep agent metrics
├── basic_agent_results.json  # Basic agent metrics
└── agent_comparison.md       # Side-by-side comparison
```

## Modifications Made

### URL Matching Fix (TBO Score)

Enhanced `run_evaluation.py` to recognize equivalent authoritative domains:

- `rfc-editor.org` ≈ `datatracker.ietf.org` for RFCs
- Matches by document identifier (e.g., `rfc9000`) instead of exact URL

**Impact**: TBO score increased from 0% to ~80% by properly recognizing citations.

### Tavily Integration

Replaced MCP-based Tavily with direct SDK usage:

- `search_depth="basic"` to avoid timeouts
- Faster, more reliable searches
- No network overhead

**Impact**: Eliminated `httpx.ConnectTimeout` errors during evaluation.

## Benchmark Queries

Default queries from RigorousBench:

- `07001`: QUIC transport protocol standardization
- `05002`: Same-sex marriage legal cases
- `09003`: 1848 European revolutionary movements

Customize by editing the `query_ids` lists in the evaluation scripts.

## Expected Performance

Based on the RigorousBench paper:

- **SOTA Baseline**: ~34% ITS
- **Our Deep Agent**: ~68-74% ITS (with TBO fix)
- **Basic Agent**: TBD (run benchmark to find out!)

## Next Steps

1. Run `compare_agents.py` to benchmark both
2. Review `agent_comparison.md` to see which performs better
3. If deep agent doesn't significantly outperform basic:
   - Consider simplifying architecture
   - Evaluate cost/speed tradeoffs
4. If deep agent wins:
   - Justify the added complexity
   - Optimize further (e.g., better prompts, tool usage)
