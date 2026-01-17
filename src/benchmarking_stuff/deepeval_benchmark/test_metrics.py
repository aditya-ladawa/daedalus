"""
Standalone Test for DeepEval Metrics

Test the metrics on existing report files without running the agent.
Useful for validating metrics before full integration.

Usage:
    python test_metrics.py --report path/to/report.md
    python test_metrics.py --report-dir path/to/reports/
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

# Import config and metrics
from config import (
    JUDGE_MODEL, 
    THRESHOLDS, 
    RESULTS_DIR,
    print_config,
)
from custom_metrics import get_all_custom_metrics

# DeepEval imports
try:
    from deepeval import evaluate
    from deepeval.test_case import LLMTestCase
    from deepeval.metrics import (
        FaithfulnessMetric,
        HallucinationMetric,
    )
    DEEPEVAL_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  DeepEval not installed: {e}")
    print("   Run: pip install deepeval")
    DEEPEVAL_AVAILABLE = False
    sys.exit(1)


def test_single_report(report_path: Path, query: str = None) -> dict:
    """
    Test metrics on a single report file.
    
    Args:
        report_path: Path to the report markdown file
        query: Optional query (extracted from filename if not provided)
    """
    print(f"\n📄 Testing: {report_path.name}")
    
    # Read report
    with open(report_path, 'r') as f:
        report_content = f.read()
    
    if not query:
        # Try to extract query from first line or filename
        first_line = report_content.split('\n')[0].strip('#').strip()
        query = first_line if first_line else report_path.stem.replace('_', ' ')
    
    print(f"   Query: {query[:60]}...")
    print(f"   Content length: {len(report_content)} chars")
    
    # Get metrics (custom only for standalone test)
    metrics = get_all_custom_metrics()
    
    # Create test case - add context for completeness
    test_case = LLMTestCase(
        input=query,
        actual_output=report_content,
        context=[],  # No ground truth for standalone test
        retrieval_context=[],  # No retrieval context for standalone test
    )
    
    # Evaluate
    print(f"   🔍 Running {len(metrics)} metrics...")
    
    try:
        evaluation_result = evaluate(
            test_cases=[test_case],
            metrics=metrics,
        )
    except Exception as e:
        print(f"   ❌ Error during evaluation: {e}")
        return {"error": str(e)}
    
    # Collect results from EvaluationResult
    results = {}
    
    if evaluation_result.test_results and len(evaluation_result.test_results) > 0:
        test_result = evaluation_result.test_results[0]
        if test_result.metrics_data:
            for metric_data in test_result.metrics_data:
                results[metric_data.name] = {
                    "score": metric_data.score,
                    "reason": metric_data.reason,
                    "passed": metric_data.success,
                    "error": metric_data.error,
                }
                
                # Print result
                if metric_data.score is not None:
                    status = "✅" if metric_data.success else "❌"
                    print(f"   {status} {metric_data.name}: {metric_data.score:.2f}")
                elif metric_data.error:
                    print(f"   ⚠️ {metric_data.name}: Error - {metric_data.error}")
    
    return {
        "report": str(report_path),
        "query": query,
        "scores": results,
    }


def test_report_directory(dir_path: Path) -> list:
    """Test all .md files in a directory"""
    results = []
    
    md_files = list(dir_path.glob("*.md"))
    print(f"\n📁 Found {len(md_files)} report files in {dir_path}")
    
    for report_file in md_files:
        result = test_single_report(report_file)
        results.append(result)
    
    return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test DeepEval metrics on existing reports"
    )
    parser.add_argument(
        "--report", "-r",
        type=str,
        help="Path to a single report .md file"
    )
    parser.add_argument(
        "--report-dir", "-d",
        type=str,
        help="Path to directory containing report .md files"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Query string (optional, extracted from report if not provided)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output JSON file path"
    )
    
    args = parser.parse_args()
    
    if not args.report and not args.report_dir:
        parser.print_help()
        print("\n❌ Error: Provide --report or --report-dir")
        return
    
    print_config()
    
    if args.report:
        report_path = Path(args.report)
        if not report_path.exists():
            print(f"❌ File not found: {report_path}")
            return
        results = [test_single_report(report_path, args.query)]
    else:
        dir_path = Path(args.report_dir)
        if not dir_path.exists():
            print(f"❌ Directory not found: {dir_path}")
            return
        results = test_report_directory(dir_path)
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    all_scores = {}
    for result in results:
        if "error" in result:
            continue
        for metric_name, data in result.get("scores", {}).items():
            if metric_name not in all_scores:
                all_scores[metric_name] = []
            if data.get("score") is not None:
                all_scores[metric_name].append(data["score"])
    
    for metric_name, scores in all_scores.items():
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {metric_name}: {avg:.2f} avg ({len(scores)} reports)")
    
    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = RESULTS_DIR / f"metric_test_{timestamp}.json"
    
    with open(output_path, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "judge_model": JUDGE_MODEL,
            "results": results,
        }, f, indent=2, default=str)
    
    print(f"\n📁 Results saved: {output_path}")


if __name__ == "__main__":
    main()
