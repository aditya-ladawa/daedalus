"""Compare Deep Agent vs Basic ReAct Agent on RigorousBench.

Runs both agents on the same queries and generates a comparison report.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

# Run both evaluations
async def run_comparison(query_ids: list[str] = None):
    """Run both agents and compare results.
    
    Args:
        query_ids: List of query IDs to evaluate (default: ["07001", "05002", "09003"])
    """
    if query_ids is None:
        query_ids = ["07001", "05002", "09003"]
    
    print("=" * 80)
    print("🔬 RIGOROUSBENCH AGENT COMPARISON")
    print("=" * 80)
    print(f"Queries: {query_ids}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Import evaluation functions
    from evaluate_basic_agent import run_evaluation as run_basic
    from evaluate_deep_agent import run_evaluation as run_deep
    
    print("\n" + "=" * 80)
    print("📊 RUNNING BASIC REACT AGENT")
    print("=" * 80)
    await run_basic(query_ids=query_ids)
    
    print("\n" + "=" * 80)
    print("📊 RUNNING DEEP RESEARCH AGENT")
    print("=" * 80)
    await run_deep(query_ids=query_ids)
    
    # Load results
    basic_results_path = Path(__file__).parent / "basic_agent_results.json"
    deep_results_path = Path(__file__).parent / "deep_agent_results.json"
    
    if not basic_results_path.exists() or not deep_results_path.exists():
        print("\n⚠️  Results files not found. Comparison skipped.")
        return
    
    basic_results = json.loads(basic_results_path.read_text())
    deep_results = json.loads(deep_results_path.read_text())
    
    # Generate comparison report
    comparison = generate_comparison_report(basic_results, deep_results)
    
    # Save comparison
    comparison_path = Path(__file__).parent / "agent_comparison.md"
    comparison_path.write_text(comparison)
    
    print("\n" + "=" * 80)
    print("📈 COMPARISON REPORT")
    print("=" * 80)
    print(comparison)
    print(f"\n✓ Full comparison saved to: {comparison_path}")


def generate_comparison_report(basic_results: list, deep_results: list) -> str:
    """Generate markdown comparison report.
    
    Args:
        basic_results: Results from basic agent
        deep_results: Results from deep agent
        
    Returns:
        Markdown formatted comparison report
    """
    # Create lookup dicts
    basic_by_id = {r["query_id"]: r for r in basic_results}
    deep_by_id = {r["query_id"]: r for r in deep_results}
    
    # Calculate averages
    def avg_metric(results, metric):
        scores = [r["metrics"][metric] for r in results if metric in r["metrics"]]
        return sum(scores) / len(scores) if scores else 0
    
    report = f"""# RigorousBench Agent Comparison Report

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overall Performance

| Metric | Basic ReAct | Deep Research | Δ (Deep - Basic) |
|--------|-------------|---------------|------------------|
| **ITS** | {avg_metric(basic_results, 'ITS'):.2%} | {avg_metric(deep_results, 'ITS'):.2%} | {(avg_metric(deep_results, 'ITS') - avg_metric(basic_results, 'ITS')):.2%} |
| **QUA** | {avg_metric(basic_results, 'QUA'):.2%} | {avg_metric(deep_results, 'QUA'):.2%} | {(avg_metric(deep_results, 'QUA') - avg_metric(basic_results, 'QUA')):.2%} |
| **SDR** | {avg_metric(basic_results, 'SDR'):.2%} | {avg_metric(deep_results, 'SDR'):.2%} | {(avg_metric(deep_results, 'SDR') - avg_metric(basic_results, 'SDR')):.2%} |
| **TBO** | {avg_metric(basic_results, 'TBO'):.2%} | {avg_metric(deep_results, 'TBO'):.2%} | {(avg_metric(deep_results, 'TBO') - avg_metric(basic_results, 'TBO')):.2%} |

## Per-Query Breakdown

"""
    
    # Compare each query
    all_query_ids = sorted(set(basic_by_id.keys()) | set(deep_by_id.keys()))
    
    for query_id in all_query_ids:
        basic = basic_by_id.get(query_id)
        deep = deep_by_id.get(query_id)
        
        report += f"### Query {query_id}\n\n"
        
        if basic and deep:
            bm = basic["metrics"]
            dm = deep["metrics"]
            
            report += "| Metric | Basic | Deep | Δ |\n"
            report += "|--------|-------|------|---|\n"
            for metric in ["ITS", "QUA", "SDR", "TBO"]:
                b_val = bm.get(metric, 0)
                d_val = dm.get(metric, 0)
                delta = d_val - b_val
                delta_str = f"+{delta:.2%}" if delta > 0 else f"{delta:.2%}"
                report += f"| {metric} | {b_val:.2%} | {d_val:.2%} | {delta_str} |\n"
            
            report += "\n**Winner:** "
            if dm["ITS"] > bm["ITS"]:
                report += "🏆 Deep Agent"
            elif dm["ITS"] < bm["ITS"]:
                report += "🏆 Basic Agent"
            else:
                report += "Tie"
            report += "\n\n"
            
        elif basic:
            report += "⚠️  Only basic agent completed\n\n"
        elif deep:
            report += "⚠️  Only deep agent completed\n\n"
        else:
            report += "❌ Neither agent completed\n\n"
    
    # Analysis section
    report += """## Analysis

### Architecture Comparison

**Basic ReAct Agent:**
- Single LangGraph ReAct agent
- Direct tool access
- No subagents or task delegation
- Simpler, faster execution

**Deep Research Agent:**
- Multi-agent orchestration
- Specialized subagents (researcher, executor)
- Task delegation and planning
- More complex, potentially more thorough

### Recommendations

"""
    
    avg_its_diff = avg_metric(deep_results, 'ITS') - avg_metric(basic_results, 'ITS')
    
    if avg_its_diff > 0.05:
        report += "✅ **Deep agent shows significant improvement** (+{:.1%}). The added complexity is justified.\n\n".format(avg_its_diff)
    elif avg_its_diff < -0.05:
        report += "⚠️  **Basic agent outperforms** ({:.1%}). Consider simplifying the deep agent architecture.\n\n".format(abs(avg_its_diff))
    else:
        report += "➖ **Performance is similar** ({:.1%} difference). Evaluate based on runtime and cost efficiency.\n\n".format(abs(avg_its_diff))
    
    return report


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Agent Comparison")
    parser.add_argument("--queries", type=str, default="07001,05002,09003", help="Comma-separated query IDs")
    args = parser.parse_args()
    
    query_ids = [q.strip() for q in args.queries.split(",")]
    
    # Run comparison on specified queries
    asyncio.run(run_comparison(query_ids))
