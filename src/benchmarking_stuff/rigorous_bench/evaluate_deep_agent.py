"""RigorousBench Evaluation Runner.

Runs the deep research agent on benchmark queries and evaluates results.
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

# Add path for config
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.config import DEEP_AGENT_MODEL, SUBAGENT_MODEL, JUDGE_MODEL

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.deep_agent import run_query

load_dotenv()

# Paths
BENCH_DIR = Path(__file__).parent
BENCHMARK_FILE = BENCH_DIR / "RigorousBench.jsonl"
REPORTS_DIR = BENCH_DIR.parent / "eval_reports" / "rigorous_bench" / "deep_agent"


def load_benchmark_queries(query_ids: list[str] = None) -> list[dict]:
    """Load queries from RigorousBench.jsonl.
    
    Args:
        query_ids: Optional list of specific UIDs to load
    
    Returns:
        List of query dicts with uid, query, qsr, tsl, fak, fdk
    """
    queries = []
    with open(BENCHMARK_FILE, "r") as f:
        for line in f:
            data = json.loads(line)
            if query_ids is None or data["uid"] in query_ids:
                queries.append(data)
    return queries


def load_report(query_id: str) -> str:
    """Load generated report for a query."""
    report_path = REPORTS_DIR / query_id / "report.md"
    if report_path.exists():
        return report_path.read_text()
    return ""


def extract_citations(report: str) -> list[str]:
    """Extract citation URLs from report."""
    # Pattern for markdown links
    url_pattern = r'\[.*?\]\((https?://[^\s\)]+)\)'
    urls = re.findall(url_pattern, report)
    
    # Also check for bare URLs
    bare_pattern = r'(?<!\[)(https?://[^\s\)]+)'
    bare_urls = re.findall(bare_pattern, report)
    
    return list(set(urls + bare_urls))


def count_keywords(report: str, keywords: list[str]) -> dict:
    """Count occurrences of keywords (case-insensitive)."""
    report_lower = report.lower()
    counts = {}
    for kw in keywords:
        counts[kw] = len(re.findall(re.escape(kw.lower()), report_lower))
    return counts


async def evaluate_with_judge(
    query: str,
    report: str,
    qsr: list[str],
    model_name: str = JUDGE_MODEL,
) -> dict:
    """Use LLM judge to evaluate report against rubrics."""
    judge = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=os.environ.get("GEMINI_API_KEY"),
        temperature=0.0,
    )
    
    # Build rubric evaluation prompt
    rubrics_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(qsr[:10])])  # First 10
    
    prompt = f"""You are an expert evaluator assessing a research report.

ORIGINAL QUERY:
{query}

REPORT:
{report[:8000]}  # Truncate for token limits

EVALUATION RUBRICS (answer each with Yes=score or No=0):
{rubrics_text}

For each rubric, provide:
1. Your verdict (Yes/No)
2. Score (from the rubric, e.g., Yes=2)
3. Brief justification

Format your response as JSON:
{{
    "rubric_scores": [
        {{"rubric": 1, "verdict": "Yes/No", "score": X, "reason": "..."}},
        ...
    ],
    "total_score": X,
    "max_possible": X,
    "overall_quality": "brief assessment"
}}
"""
    
    try:
        response = await judge.ainvoke([{"role": "user", "content": prompt}])
        content = response.content
        
        # Try to parse JSON from response
        if isinstance(content, list):
            content = content[0].get("text", str(content))
        
        # Extract JSON block
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
        
        return {"raw_response": content, "error": "Could not parse JSON"}
        
    except Exception as e:
        return {"error": str(e)}


def calculate_metrics(report: str, query_data: dict, eval_result: dict) -> dict:
    """Calculate RigorousBench metrics."""
    # FAK/FDK keyword analysis
    fak_counts = count_keywords(report, query_data.get("fak", []))
    fdk_counts = count_keywords(report, query_data.get("fdk", []))
    
    fak_total = sum(fak_counts.values())
    fdk_total = sum(fdk_counts.values())
    
    # Semantic Drift Ratio (SDR) - higher is better
    sdr = fak_total / max(fak_total + fdk_total, 1)
    
    # URL matching with equivalent domain mapping
    report_urls = extract_citations(report)
    trusted_urls = query_data.get("tsl", [])
    
    # Map of equivalent authoritative domains
    EQUIVALENT_DOMAINS = {
        # RFC sources
        "rfc-editor.org": ["datatracker.ietf.org", "ietf.org"],
        "datatracker.ietf.org": ["rfc-editor.org", "ietf.org"],
    }
    
    def normalize_url(url):
        """Normalize URL for comparison"""
        url = url.lower().rstrip("/")
        url = re.sub(r'^https?://(www\.)?', '', url)
        return url
    
    def extract_domain_and_path(url):
        """Extract domain and path from normalized URL"""
        parts = url.split("/", 1)
        domain = parts[0]
        path = "/" + parts[1] if len(parts) > 1 else ""
        return domain, path
    
    def urls_match(trusted_url, report_url):
        """Check if two URLs match, considering equivalent domains"""
        t_domain, t_path = extract_domain_and_path(trusted_url)
        r_domain, r_path = extract_domain_and_path(report_url)
        
        # Direct substring match (original logic)
        if trusted_url in report_url:
            return True
        
        # Check if domains are equivalent
        equivalent_domains = EQUIVALENT_DOMAINS.get(t_domain, [t_domain])
        if r_domain in equivalent_domains or t_domain == r_domain:
            # For RFC documents, match by document identifier
            if "rfc" in t_path.lower() or "draft-ietf" in t_path.lower():
                rfc_match_t = re.search(r'(rfc\d+|draft-ietf-[\w-]+)', t_path.lower())
                rfc_match_r = re.search(r'(rfc\d+|draft-ietf-[\w-]+)', r_path.lower())
                if rfc_match_t and rfc_match_r:
                    return rfc_match_t.group(1) == rfc_match_r.group(1)
            # For other paths
            if t_path and r_path and (t_path in r_path or r_path in t_path):
                return True
        
        return False
    
    report_normalized = [normalize_url(u) for u in report_urls]
    trusted_normalized = [normalize_url(u) for u in trusted_urls]
    
    matches = sum(1 for trusted in trusted_normalized 
                  if any(urls_match(trusted, report) for report in report_normalized))
    tbo = matches / max(len(trusted_normalized), 1)  # Trust Boost
    
    # Quality score from judge
    qua = eval_result.get("total_score", 0) / max(eval_result.get("max_possible", 1), 1)
    
    # Integrated Total Score
    its = (0.5 * qua) + (0.3 * sdr) + (0.2 * tbo)
    
    return {
        "QUA": round(qua, 4),
        "SDR": round(sdr, 4),
        "TBO": round(tbo, 4),
        "ITS": round(its, 4),
        "fak_matches": fak_total,
        "fdk_matches": fdk_total,
        "url_matches": matches,
        "total_trusted_urls": len(trusted_urls),
    }


def write_evaluation_report(
    query_id: str,
    query_data: dict,
    eval_result: dict,
    metrics: dict,
) -> str:
    """Generate evaluation markdown report."""
    report = f"""# Evaluation Report: {query_id}

## Query
{query_data['query']}

## Metrics Summary

| Metric | Score | Description |
|--------|-------|-------------|
| **QUA** | {metrics['QUA']:.2%} | Semantic Quality (rubric adherence) |
| **SDR** | {metrics['SDR']:.2%} | Semantic Drift Ratio (focus) |
| **TBO** | {metrics['TBO']:.2%} | Trust Boost (authoritative sources) |
| **ITS** | {metrics['ITS']:.2%} | Integrated Total Score |

## Keyword Analysis

- **Focus Keywords (FAK) matched**: {metrics['fak_matches']}
- **Deviation Keywords (FDK) matched**: {metrics['fdk_matches']}
- **Trusted URLs matched**: {metrics['url_matches']}/{metrics['total_trusted_urls']}

## Rubric Evaluation

"""
    
    if "rubric_scores" in eval_result:
        for item in eval_result["rubric_scores"]:
            verdict = "✅" if item.get("verdict") == "Yes" else "❌"
            report += f"- {verdict} Rubric {item.get('rubric')}: Score {item.get('score')} - {item.get('reason', 'N/A')}\n"
    
    if "overall_quality" in eval_result:
        report += f"\n## Overall Assessment\n{eval_result['overall_quality']}\n"
    
    return report


async def run_evaluation(
    query_ids: list[str],
    main_model: str = DEEP_AGENT_MODEL,
    subagent_model: str = SUBAGENT_MODEL,
    judge_model: str = JUDGE_MODEL,
):
    """Run full evaluation pipeline."""
    print(f"🔬 RigorousBench Evaluation")
    print(f"   Queries: {query_ids}")
    print(f"   Main Agent: {main_model}")
    print(f"   Subagents: {subagent_model}")
    print(f"   Judge: {judge_model}")
    print("=" * 60)
    
    # Load benchmark data
    queries = load_benchmark_queries(query_ids)
    print(f"   Loaded {len(queries)} queries")
    
    results = []
    
    for qdata in queries:
        uid = qdata["uid"]
        query = qdata["query"]
        
        print(f"\n📝 Processing {uid}: {query[:60]}...")
        
        try:
            # Step 1: Run agent
            response = await run_query(query, uid, main_model, subagent_model)
            print(f"   ✓ Agent completed")
            
            # Step 2: Ensure report exists or use response
            report = load_report(uid)
            if not report:
                print(f"   ⚠ No report found. Saving raw response...")
                report_path = REPORTS_DIR / uid / "report.md"
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(response)
                report = response
            
            # Step 3: Evaluate
            print(f"   → Evaluating with judge...")
            eval_result = await evaluate_with_judge(
                query=query,
                report=report,
                qsr=qdata.get("qsr", []),
                model_name=judge_model,
            )
            
            # Step 4: Metrics
            metrics = calculate_metrics(report, qdata, eval_result)
            print(f"   → Metrics: ITS={metrics['ITS']:.2%}")
            
            # Step 5: Save eval result
            eval_report = write_evaluation_report(uid, qdata, eval_result, metrics)
            (REPORTS_DIR / uid / "evaluation.md").write_text(eval_report)
            
            results.append({
                "uid": uid,
                "metrics": metrics,
                "eval_result": eval_result,
            })
            
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Save results
    if results:
        results_file = BENCH_DIR / "deep_agent_results.json"
        json_dump = [{"query_id": r["uid"], "metrics": r["metrics"], "eval": r["eval_result"]} for r in results]
        results_file.write_text(json.dumps(json_dump, indent=2))
        print(f"\n✓ Results saved to {results_file}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run RigorousBench evaluation")
    parser.add_argument(
        "--queries",
        type=str,
        default="07001,05002,09003",
        help="Comma-separated query UIDs",
    )
    parser.add_argument(
        "--main-model",
        type=str,
        default=DEEP_AGENT_MODEL,
        help="Main agent model",
    )
    parser.add_argument(
        "--subagent-model",
        type=str,
        default=SUBAGENT_MODEL,
        help="Subagent model",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default=JUDGE_MODEL,
        help="Judge model",
    )
    
    args = parser.parse_args()
    query_ids = [q.strip() for q in args.queries.split(",")]
    
    asyncio.run(run_evaluation(
        query_ids,
        args.main_model,
        args.subagent_model,
        args.judge_model,
    ))
