"""Run your Deep/Basic agent on Deep Research Bench queries.

Usage (from deep_research_bench directory):
    # Run on a single query
    python run_agent.py --agent deep --output deep_agent --query 51
    
    # Run on first 3 queries (quick test)
    python run_agent.py --agent deep --output deep_agent --quick
    
    # Run on all 100 queries
    python run_agent.py --agent deep --output deep_agent

Then run evaluation:
    bash run_benchmark.sh
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths - relative to deep_research_bench directory
BENCH_DIR = Path(__file__).parent
QUERIES_FILE = BENCH_DIR / "data" / "prompt_data" / "query.jsonl"
OUTPUT_DIR = BENCH_DIR / "data" / "test_data" / "raw_data"

# Add parent path to import agents
sys.path.insert(0, str(BENCH_DIR.parent))

from agents.deep_agent import run_query as run_deep_query
from agents.basic_agent import run_query as run_basic_query

# Reports are saved to rigorous_bench by agents
REPORTS_BASE = BENCH_DIR.parent / "rigorous_bench"


def load_benchmark_queries(limit: int = None) -> list[dict]:
    """Load Deep Research Bench queries from data/prompt_data/query.jsonl."""
    queries = []
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))
                if limit and len(queries) >= limit:
                    break
    return queries


async def run_agent_on_query(
    query_data: dict,
    agent_type: str,
) -> dict:
    """Run agent on a single query and return formatted result."""
    query_id = str(query_data["id"])
    prompt = query_data["prompt"]
    
    print(f"\n{'='*80}")
    print(f"📝 Query {query_id}: {prompt[:100]}...")
    print(f"{'='*80}")
    
    try:
        if agent_type == "deep":
            await run_deep_query(query=prompt, query_id=query_id)
            report_path = REPORTS_BASE / "eval_reports" / "deep_research_bench" / "deep_agent" / query_id / "report.md"
        else:
            await run_basic_query(query=prompt, query_id=query_id)
            report_path = REPORTS_BASE / "eval_reports" / "deep_research_bench" / "basic_agent" / query_id / "report.md"
        
        if report_path.exists():
            article = report_path.read_text(encoding="utf-8")
            print(f"✓ Report generated ({len(article)} chars)")
            # Keep ID as integer, include language for FACT evaluation
            return {
                "id": query_data["id"],  # Keep as integer to match query.jsonl
                "prompt": prompt,
                "article": article,
                "language": query_data.get("language", "en")
            }
        else:
            print(f"✗ Report not found at {report_path}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def run_benchmark(agent_type: str, output_name: str, limit: int = None, start_from: int = 0):
    """Run agent on benchmark queries and save to data/test_data/raw_data/<output>.jsonl."""
    print(f"""
{'='*80}
🔬 Deep Research Bench - Agent Runner
{'='*80}
Agent: {agent_type.upper()}
Output: {output_name}
Limit: {limit or 'All (100)'}
Start From: {start_from}
{'='*80}
""")
    
    queries = load_benchmark_queries(limit)
    if start_from > 0:
        queries = queries[start_from:]
    
    output_file = OUTPUT_DIR / f"{output_name}.jsonl"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    successful = 0
    for i, query_data in enumerate(queries, start=start_from + 1):
        print(f"\n[{i}/{len(queries) + start_from}] Query {query_data['id']}...")
        
        result = await run_agent_on_query(query_data, agent_type)
        
        if result:
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            successful += 1
    
    print(f"""
{'='*80}
✅ Complete: {successful}/{len(queries)} queries
Output: {output_file}
{'='*80}

Next: Edit run_benchmark.sh, set TARGET_MODELS=("{output_name}"), then run: bash run_benchmark.sh
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run agents on Deep Research Bench queries")
    parser.add_argument("--agent", type=str, required=True, choices=["deep", "basic"])
    parser.add_argument("--output", type=str, required=True, help="Output name (e.g., 'deep_agent')")
    parser.add_argument("--query", type=str, default=None, help="Single query ID")
    parser.add_argument("--quick", action="store_true", help="First 3 queries only")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start-from", type=int, default=0)
    
    args = parser.parse_args()
    
    if args.quick:
        args.limit = 3
    
    if args.query:
        # Single query mode
        all_queries = load_benchmark_queries()
        target = next((q for q in all_queries if str(q["id"]) == str(args.query)), None)
        
        if not target:
            print(f"❌ Query {args.query} not found (valid: 1-100)")
            sys.exit(1)
        
        async def run_single():
            result = await run_agent_on_query(target, args.agent)
            if result:
                output_file = OUTPUT_DIR / f"{args.output}.jsonl"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                print(f"\n✓ Saved to {output_file}")
        
        asyncio.run(run_single())
    else:
        asyncio.run(run_benchmark(args.agent, args.output, args.limit, args.start_from))
