"""RigorousBench Evaluation for Basic ReAct Agent.

Runs the basic ReAct agent on benchmark queries and evaluates results.
Results are saved separately from the deep agent for comparison.
"""

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add path for config
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.config import BASIC_AGENT_MODEL, JUDGE_MODEL

from agents.basic_agent import run_query as run_basic_query
from evaluate_deep_agent import (
    load_benchmark_queries,
    load_report,
    evaluate_with_judge,
    calculate_metrics,
    write_evaluation_report,
)

load_dotenv()

# Paths
BENCH_DIR = Path(__file__).parent
BENCHMARK_FILE = BENCH_DIR / "RigorousBench.jsonl"
REPORTS_DIR = BENCH_DIR.parent / "eval_reports" / "rigorous_bench" / "basic_agent"


async def run_evaluation(
    query_ids: list[str],
    agent_model: str = BASIC_AGENT_MODEL,
    judge_model: str = JUDGE_MODEL,
):
    """Run evaluation pipeline for basic agent.
    
    Args:
        query_ids: List of query UIDs to evaluate
        agent_model: Model for the basic agent
        judge_model: Model for judge evaluation
    """
    print(f"""🔬 RigorousBench Evaluation - Basic ReAct Agent
   Queries: {query_ids}
   Agent Model: {agent_model}
   Judge Model: {judge_model}
{'='*60}""")
    
    # Load benchmark queries
    queries = load_benchmark_queries(query_ids)
    print(f"   Loaded {len(queries)} queries\n")
    
    results = []
    
    for query_data in queries:
        query_id = query_data["uid"]
        query = query_data["query"]
        qsr = query_data.get("qsr", [])
        
        print(f"📝 Processing {query_id}: {query[:70]}...")
        
        # Run basic agent
        try:
            report_path = await run_basic_query(
                query=query,
                query_id=query_id,
                model=agent_model,
            )
            
            # Load generated report
            report = (REPORTS_DIR / query_id / "report.md").read_text()
            
            if not report or len(report) < 100:
                print(f"   ⚠️  Report too short ({len(report)} chars)")
                continue
            
            # Evaluate with judge
            eval_result = await evaluate_with_judge(
                query=query,
                report=report,
                qsr=qsr,
                model_name=judge_model,
            )
            
            # Calculate metrics
            metrics = calculate_metrics(report, query_data, eval_result)
            
            # Write evaluation report
            eval_report = write_evaluation_report(query_id, query_data, eval_result, metrics)
            eval_path = REPORTS_DIR / query_id / "evaluation.md"
            eval_path.write_text(eval_report)
            
            print(f"   ✓ ITS={metrics['ITS']:.2%} | QUA={metrics['QUA']:.2%} | SDR={metrics['SDR']:.2%} | TBO={metrics['TBO']:.2%}")
            
            results.append({
                "query_id": query_id,
                "metrics": metrics,
                "eval": eval_result,
            })
            
        except Exception as e:
            print(f"   ✗ Agent failed: {e}")
            continue
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 EVALUATION SUMMARY - BASIC AGENT")
    print(f"{'='*60}")
    
    if results:
        for result in results:
            m = result["metrics"]
            print(f"{result['query_id']}: ITS={m['ITS']:.2%} | QUA={m['QUA']:.2%} | SDR={m['SDR']:.2%} | TBO={m['TBO']:.2%}")
        
        avg_its = sum(r["metrics"]["ITS"] for r in results) / len(results)
        print(f"\nAverage ITS: {avg_its:.2%}")
        
        # Save results
        results_file = BENCH_DIR / "basic_agent_results.json"
        results_file.write_text(json.dumps(results, indent=2))
        print(f"\n✓ Results saved to: {results_file}")
    else:
        print("No successful evaluations.")


if __name__ == "__main__":
    # Evaluate on the same queries as deep agent
    query_ids = ["07001", "05002", "09003"]
    asyncio.run(run_evaluation(query_ids))
