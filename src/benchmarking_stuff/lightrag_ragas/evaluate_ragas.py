"""
RAGAS Evaluation Script for LightRAG

Evaluates LightRAG retrieval quality across 4 modes (naive, local, global, hybrid)
using RAGAS metrics: Faithfulness, Answer Relevancy, Context Recall, Context Precision.

Usage:
    # Quick test (10 questions)
    python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --quick
    
    # Full evaluation (all 60 questions)
    python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py
    
    # Single mode evaluation
    python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --modes hybrid
    
    # Custom dataset
    python src/benchmarking_stuff/lightrag_ragas/evaluate_ragas.py --dataset custom.json
"""

import asyncio
import json
import os
import sys
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

# Retry with exponential backoff
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        before_sleep_log,
        wait_random_exponential,
    )
    import logging
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    print("⚠️  tenacity not installed. Retry logic disabled.")
    print("   Run: pip install tenacity")

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "rag"))

from dotenv import load_dotenv
load_dotenv()

# LightRAG imports
from lightrag import QueryParam
from config import get_rag_instance

# RAGAS imports
try:
    from datasets import Dataset
    from ragas import evaluate
    # Use new import path (ragas v1.0 compatible)
    from ragas.metrics._faithfulness import Faithfulness
    from ragas.metrics._answer_relevance import AnswerRelevancy
    from ragas.metrics._context_recall import ContextRecall
    from ragas.metrics._context_precision import ContextPrecision
    from ragas.metrics._answer_correctness import AnswerCorrectness
    from ragas.metrics._answer_similarity import AnswerSimilarity
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    RAGAS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  RAGAS not installed: {e}")
    print("   Run: pip install ragas datasets")
    RAGAS_AVAILABLE = False

# LangChain imports for Gemini (judge LLM)
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGCHAIN_GEMINI_AVAILABLE = True
except ImportError:
    print("⚠️  langchain-google-genai not installed")
    print("   Run: pip install langchain-google-genai")
    LANGCHAIN_GEMINI_AVAILABLE = False

# LangChain OpenAI imports for OpenRouter embeddings
try:
    from langchain_openai import OpenAIEmbeddings
    LANGCHAIN_OPENAI_AVAILABLE = True
except ImportError:
    print("⚠️  langchain-openai not installed")
    print("   Run: pip install langchain-openai")
    LANGCHAIN_OPENAI_AVAILABLE = False


# =============================================================================
# CONFIGURATION
# =============================================================================

# LightRAG query parameters
TOP_K = 30          # Graph entities/relationships to retrieve
CHUNK_TOP_K = 8     # Text chunks to retrieve

# Query modes to evaluate
QUERY_MODES = ["naive", "local", "global", "hybrid"]

# Judge LLM for RAGAS
JUDGE_MODEL = "gemini-2.5-flash"  # Fast and cheap for evaluation

# Embedding model via OpenRouter (Qwen3 embedding series)
# Options: qwen/qwen3-embedding-0.6b | qwen/qwen3-embedding-4b | qwen/qwen3-embedding-8b
EMBEDDING_MODEL = "qwen/qwen3-embedding-4b"

# Results directory
RESULTS_DIR = Path(__file__).parent / "results"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_contexts(raw_context: str) -> list[str]:
    """
    Parse LightRAG raw context output into list of text chunks.
    
    LightRAG returns context as a structured string with entities,
    relationships, and source text. We extract meaningful chunks.
    """
    if not raw_context:
        return [""]
    
    # Split by common delimiters and filter empty chunks
    chunks = []
    
    # Strategy 1: Split by double newlines
    parts = raw_context.split("\n\n")
    
    for part in parts:
        part = part.strip()
        if part and len(part) > 50:  # Filter out very short fragments
            chunks.append(part)
    
    # If we get too few chunks, return the whole context as one chunk
    if len(chunks) < 2:
        chunks = [raw_context[:8000]]  # Limit to avoid token issues
    
    # Limit to top chunks to avoid context overflow
    return chunks[:CHUNK_TOP_K] if chunks else ["No context retrieved"]


def calculate_ragas_score(metrics: dict) -> float:
    """Calculate overall RAGAS score (average of all metrics)."""
    values = [v for v in metrics.values() if v is not None and not (isinstance(v, float) and v != v)]  # Filter NaN
    return sum(values) / len(values) if values else 0.0


# =============================================================================
# EVALUATION FUNCTIONS
# =============================================================================

async def evaluate_single_question(
    rag,
    question: str,
    ground_truth: str,
    mode: str,
    topic: str = "",
) -> dict:
    """
    Evaluate a single question with LightRAG.
    
    Returns:
        dict with question, topic, contexts, answer, ground_truth
    """
    try:
        # Get retrieved contexts (raw)
        contexts_raw = await rag.aquery(
            question,
            param=QueryParam(
                mode=mode,
                top_k=TOP_K,
                chunk_top_k=CHUNK_TOP_K,
                only_need_context=True,  # Get raw context, not LLM answer
                enable_rerank=False
            )
        )
        
        # Get LightRAG's generated answer
        answer = await rag.aquery(
            question,
            param=QueryParam(
                mode=mode,
                top_k=TOP_K,
                chunk_top_k=CHUNK_TOP_K,
                enable_rerank=False
            )
        )
        
        # Parse contexts into list
        contexts = parse_contexts(contexts_raw)
        
        return {
            "question": question,
            "topic": topic,
            "contexts": contexts,
            "answer": answer,
            "ground_truth": ground_truth,
            "success": True
        }
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return {
            "question": question,
            "topic": topic,
            "contexts": ["Error retrieving context"],
            "answer": f"Error: {str(e)}",
            "ground_truth": ground_truth,
            "success": False
        }


async def evaluate_mode(
    rag,
    dataset: list[dict],
    mode: str,
    judge_llm,
    embeddings,
    progress_callback=None,
) -> dict:
    """
    Evaluate LightRAG with a specific mode using RAGAS.
    
    Args:
        rag: LightRAG instance
        dataset: List of {question, ground_truth} dicts
        mode: Query mode (naive, local, global, hybrid)
        judge_llm: RAGAS LLM wrapper for evaluation
        embeddings: RAGAS embeddings wrapper
        progress_callback: Optional callback for progress updates
    
    Returns:
        dict with metrics and individual results
    """
    print(f"\n{'='*60}")
    print(f"📊 Evaluating mode: {mode.upper()}")
    print(f"{'='*60}")
    
    results = []
    start_time = time.time()
    
    for i, item in enumerate(dataset):
        if progress_callback:
            progress_callback(i + 1, len(dataset), mode)
        else:
            print(f"  [{i+1}/{len(dataset)}] Processing: {item['question'][:50]}...")
        
        result = await evaluate_single_question(
            rag,
            item["question"],
            item["ground_truth"],
            mode,
            item.get("topic", "")
        )
        results.append(result)
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)
    
    elapsed = time.time() - start_time
    print(f"  ⏱️  Query time: {elapsed:.1f}s ({elapsed/len(dataset):.2f}s/question)")
    
    # Filter successful results
    successful = [r for r in results if r["success"]]
    failed_count = len(results) - len(successful)
    
    if failed_count > 0:
        print(f"  ⚠️  {failed_count} questions failed")
    
    if not successful:
        print("  ❌ All questions failed - skipping RAGAS evaluation")
        return {
            "mode": mode,
            "metrics": {},
            "ragas_score": 0.0,
            "results": results,
            "elapsed_time": elapsed,
            "success_count": 0,
            "failed_count": len(results)
        }
    
    # Convert to RAGAS dataset format
    print(f"  🔍 Running RAGAS evaluation with {len(successful)} questions...")
    
    ragas_data = {
        "question": [r["question"] for r in successful],
        "contexts": [r["contexts"] for r in successful],
        "answer": [r["answer"] for r in successful],
        "ground_truth": [r["ground_truth"] for r in successful],
        "topic": [r.get("topic", "") for r in successful]
    }
    
    ragas_dataset = Dataset.from_dict(ragas_data)
    
    # Run RAGAS evaluation with retry logic
    def run_ragas_eval():
        """Run RAGAS evaluation (wrapped for retry)"""
        return evaluate(
            ragas_dataset,
            metrics=[
                Faithfulness(),
                AnswerRelevancy(),
                ContextRecall(),
                ContextPrecision(),
                AnswerCorrectness(),
                AnswerSimilarity(),
            ],
            llm=judge_llm,
            embeddings=embeddings,
        )
    
    try:
        # Retry with exponential backoff for rate limit errors
        max_retries = 5
        base_wait = 10  # seconds
        max_wait = 120  # seconds
        
        for attempt in range(max_retries):
            try:
                eval_result = run_ragas_eval()
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e).lower()
                # Check if it's a retryable error (429, quota, timeout, resource exhausted)
                is_retryable = any(x in error_str for x in [
                    '429', 'rate limit', 'quota', 'resource exhausted',
                    'timeout', 'too many requests', 'overloaded'
                ])
                
                if is_retryable and attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = min(base_wait * (2 ** attempt) + random.uniform(0, 5), max_wait)
                    print(f"  ⚠️  Rate limit hit (attempt {attempt + 1}/{max_retries}). Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    raise  # Not retryable or out of retries
        
        # Convert to pandas DataFrame to extract metrics
        results_df = eval_result.to_pandas()
        
        # Helper to safely get mean (handles NaN)
        def safe_mean(col_name):
            if col_name in results_df:
                return results_df[col_name].dropna().mean()
            return 0.0
        
        # Extract metrics (mean across all questions)
        metrics = {
            "faithfulness": safe_mean("faithfulness"),
            "answer_relevancy": safe_mean("answer_relevancy"),
            "context_recall": safe_mean("context_recall"),
            "context_precision": safe_mean("context_precision"),
            "answer_correctness": safe_mean("answer_correctness"),
            "answer_similarity": safe_mean("answer_similarity"),
        }
        
        ragas_score = calculate_ragas_score(metrics)
        
        # Helper to safely get value (handles NaN)
        def safe_val(row, key):
            val = row.get(key, 0)
            if val is None or (isinstance(val, float) and val != val):  # NaN check
                return 0.0
            return float(val)
        
        # Calculate per-question RAGAS scores
        per_question_scores = []
        for (idx, row), orig_result in zip(results_df.iterrows(), successful):
            q_scores = {
                "question": orig_result.get("question", f"Q{idx+1}"),
                "topic": orig_result.get("topic", ""),
                "faithfulness": safe_val(row, "faithfulness"),
                "answer_relevancy": safe_val(row, "answer_relevancy"),
                "context_recall": safe_val(row, "context_recall"),
                "context_precision": safe_val(row, "context_precision"),
                "answer_correctness": safe_val(row, "answer_correctness"),
                "answer_similarity": safe_val(row, "answer_similarity"),
            }
            # Calculate per-question RAGAS score (average of all 6 metrics)
            q_scores["ragas_score"] = sum([
                q_scores["faithfulness"],
                q_scores["answer_relevancy"],
                q_scores["context_recall"],
                q_scores["context_precision"],
                q_scores["answer_correctness"],
                q_scores["answer_similarity"],
            ]) / 6
            per_question_scores.append(q_scores)
        
        print(f"  ✅ Faithfulness:       {metrics['faithfulness']:.4f}")
        print(f"  ✅ Answer Relevancy:   {metrics['answer_relevancy']:.4f}")
        print(f"  ✅ Context Recall:     {metrics['context_recall']:.4f}")
        print(f"  ✅ Context Precision:  {metrics['context_precision']:.4f}")
        print(f"  ✅ Answer Correctness: {metrics['answer_correctness']:.4f}")
        print(f"  ✅ Answer Similarity:  {metrics['answer_similarity']:.4f}")
        print(f"  📈 RAGAS Score:        {ragas_score:.4f}")
        
    except Exception as e:
        print(f"  ❌ RAGAS evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        metrics = {}
        ragas_score = 0.0
        per_question_scores = []
    
    total_elapsed = time.time() - start_time
    
    return {
        "mode": mode,
        "metrics": metrics,
        "ragas_score": ragas_score,
        "per_question_scores": per_question_scores,  # NEW: per-question breakdown
        "results": results,
        "elapsed_time": total_elapsed,
        "success_count": len(successful),
        "failed_count": failed_count
    }


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_markdown_report(all_results: list[dict], output_path: Path) -> str:
    """Generate a markdown comparison report with per-question scores."""
    
    lines = [
        "# LightRAG RAGAS Evaluation Report",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary (Average Scores)",
        "",
        "| Mode | Faith. | Ans.Rel. | Ctx.Rec. | Ctx.Prec. | Ans.Corr. | Ans.Sim. | RAGAS |",
        "|------|--------|----------|----------|-----------|-----------|----------|-------|"
    ]
    
    for result in all_results:
        mode = result["mode"]
        m = result.get("metrics", {})
        ragas = result.get("ragas_score", 0)
        
        lines.append(
            f"| {mode:8} | {m.get('faithfulness', 0):.3f} | "
            f"{m.get('answer_relevancy', 0):.3f} | "
            f"{m.get('context_recall', 0):.3f} | "
            f"{m.get('context_precision', 0):.3f} | "
            f"{m.get('answer_correctness', 0):.3f} | "
            f"{m.get('answer_similarity', 0):.3f} | "
            f"**{ragas:.3f}** |"
        )
    
    # Find best mode
    best_result = max(all_results, key=lambda x: x.get("ragas_score", 0))
    best_mode = best_result["mode"]
    best_score = best_result.get("ragas_score", 0)
    
    lines.extend([
        "",
        "## Key Findings",
        "",
        f"- **Best Overall Mode**: {best_mode.upper()} (RAGAS Score: {best_score:.4f})",
    ])
    
    # Mode-specific insights
    for result in all_results:
        mode = result["mode"]
        m = result.get("metrics", {})
        
        if m:
            best_metric = max(m.items(), key=lambda x: x[1])
            worst_metric = min(m.items(), key=lambda x: x[1])
            lines.append(f"- **{mode.upper()}**: Best at {best_metric[0]} ({best_metric[1]:.3f}), "
                        f"weakest at {worst_metric[0]} ({worst_metric[1]:.3f})")
    
    # Per-Question Scores Section
    lines.extend([
        "",
        "---",
        "",
        "## Per-Question Scores",
        ""
    ])
    
    for result in all_results:
        mode = result["mode"]
        per_q = result.get("per_question_scores", [])
        
        if not per_q:
            continue
        
        lines.extend([
            f"### Mode: {mode.upper()}",
            "",
            "| Q# | Topic | Question (truncated) | Faith. | Ans.Rel. | Ctx.Rec. | Ctx.Prec. | Ans.Corr. | Ans.Sim. | RAGAS |",
            "|----|-------|----------------------|--------|----------|----------|-----------|-----------|----------|-------|"
        ])
        
        for i, q in enumerate(per_q, 1):
            topic_text = q.get("topic", "").replace("|", "/")
            question_text = q.get("question", "").replace("|", "/")
            
            lines.append(
                f"| {i:2} | {topic_text} | {question_text} | "
                f"{q.get('faithfulness', 0):.3f} | "
                f"{q.get('answer_relevancy', 0):.3f} | "
                f"{q.get('context_recall', 0):.3f} | "
                f"{q.get('context_precision', 0):.3f} | "
                f"{q.get('answer_correctness', 0):.3f} | "
                f"{q.get('answer_similarity', 0):.3f} | "
                f"**{q.get('ragas_score', 0):.3f}** |"
            )
        
        lines.extend(["", ""])
    
    report = "\n".join(lines)
    
    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)
    
    return report


# =============================================================================
# MAIN
# =============================================================================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="RAGAS Evaluation for LightRAG Retrieval Modes"
    )
    parser.add_argument(
        "--dataset", "-d",
        type=str,
        default="dataset_one.json",
        help="Path to benchmark dataset JSON file"
    )
    parser.add_argument(
        "--modes", "-m",
        nargs="+",
        choices=QUERY_MODES,
        default=QUERY_MODES,
        help="Query modes to evaluate (default: all)"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick test with first 10 questions only"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Limit number of questions to evaluate"
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge existing mode results from individual JSON files"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory for results (default: results/)"
    )
    
    args = parser.parse_args()
    
    # Set output directory
    global RESULTS_DIR
    if args.output_dir:
        RESULTS_DIR = Path(args.output_dir)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Handle merge mode
    if args.merge:
        print("=" * 70)
        print("🔗 MERGE MODE: Combining existing mode results")
        print("=" * 70)
        
        # Find all mode result files
        mode_files = list(RESULTS_DIR.glob("*_results.json"))
        if not mode_files:
            print(f"❌ No mode result files found in {RESULTS_DIR}")
            print("   Expected files like: naive_results.json, local_results.json, etc.")
            return
        
        print(f"\n📂 Found {len(mode_files)} mode result files:")
        all_results = []
        for mode_file in sorted(mode_files):
            print(f"   - {mode_file.name}")
            with open(mode_file, 'r') as f:
                mode_data = json.load(f)
                all_results.append(mode_data)
        
        # Generate unified report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = RESULTS_DIR / f"unified_report_{timestamp}.md"
        report = generate_markdown_report(all_results, report_path)
        print(f"\n📄 Unified report saved: {report_path}")
        
        # Save unified JSON
        json_path = RESULTS_DIR / f"unified_evaluation_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "merged_from": [str(f.name) for f in mode_files],
                "results": all_results
            }, f, indent=2)
        print(f"📁 Unified JSON saved: {json_path}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 MERGED RESULTS SUMMARY")
        print("=" * 70)
        best_result = max(all_results, key=lambda x: x.get("ragas_score", 0))
        for result in all_results:
            mode = result["mode"]
            score = result.get("ragas_score", 0)
            marker = "👑" if mode == best_result["mode"] else "  "
            print(f"{marker} {mode:8}: RAGAS Score = {score:.4f}")
        print("=" * 70)
        print(f"🏆 Best Mode: {best_result['mode'].upper()} ({best_result['ragas_score']:.4f})")
        print("=" * 70)
        return
    
    # Check dependencies
    if not RAGAS_AVAILABLE or not LANGCHAIN_GEMINI_AVAILABLE or not LANGCHAIN_OPENAI_AVAILABLE:
        print("❌ Missing dependencies. Please install:")
        print("   pip install ragas datasets langchain-google-genai langchain-openai")
        sys.exit(1)
    
    # Check API keys
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        print("❌ GEMINI_API_KEY or GOOGLE_API_KEY environment variable required")
        sys.exit(1)
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("❌ OPENROUTER_API_KEY environment variable required for embeddings")
        sys.exit(1)
    
    print("=" * 70)
    print("🔍 LightRAG RAGAS Evaluation")
    print("=" * 70)
    
    # Load dataset
    dataset_path = Path(__file__).parent / args.dataset
    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        sys.exit(1)
    
    with open(dataset_path) as f:
        dataset = json.load(f)
    
    # Apply limits
    if args.quick:
        dataset = dataset[:2]
        print(f"🚀 Quick mode: Using first 2 questions")
    elif args.limit:
        dataset = dataset[:args.limit]
        print(f"📝 Limited to {args.limit} questions")
    
    print(f"📂 Dataset: {dataset_path.name} ({len(dataset)} questions)")
    print(f"🎯 Modes: {', '.join(args.modes)}")
    print(f"⚙️  Top K: {TOP_K} (graph), {CHUNK_TOP_K} (chunks)")
    print("=" * 70)
    
    # Initialize Judge LLM for RAGAS
    print("\n🤖 Initializing Judge LLM (Gemini) + Embeddings (OpenRouter Qwen3)...")
    
    gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
    
    judge_llm = LangchainLLMWrapper(
        ChatGoogleGenerativeAI(
            model=JUDGE_MODEL,
            google_api_key=gemini_api_key,
            temperature=0
        )
    )
    
    embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
    )
    
    print(f"  Judge Model:     {JUDGE_MODEL} (Gemini)")
    print(f"  Embedding Model: {EMBEDDING_MODEL} (OpenRouter)")
    
    # Initialize LightRAG
    print("\n🗄️  Initializing LightRAG...")
    # Use absolute path to project root's lightrag database
    lightrag_db_path = str(PROJECT_ROOT / "lightrag_data_local")
    print(f"  Database: {lightrag_db_path}")
    rag = await get_rag_instance(working_dir=lightrag_db_path)
    
    # Evaluate each mode
    all_results = []
    
    for mode in args.modes:
        result = await evaluate_mode(
            rag, dataset, mode, judge_llm, embeddings
        )
        all_results.append(result)
    
    # Cleanup
    await rag.finalize_storages()
    
    # Save results (both unified and per-mode)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save individual mode results for future merging
    for r in all_results:
        mode_file = RESULTS_DIR / f"{r['mode']}_results.json"
        with open(mode_file, "w") as f:
            json.dump(r, f, indent=2)
        print(f"💾 Saved {r['mode']} results: {mode_file.name}")
    
    # Save unified JSON results
    json_path = RESULTS_DIR / f"evaluation_{timestamp}.json"
    with open(json_path, "w") as f:
        # Convert results to JSON-serializable format
        json_results = []
        for r in all_results:
            json_r = {
                "mode": r["mode"],
                "metrics": r["metrics"],
                "ragas_score": r["ragas_score"],
                "per_question_scores": r.get("per_question_scores", []),  # Per-question breakdown
                "elapsed_time": r["elapsed_time"],
                "success_count": r["success_count"],
                "failed_count": r["failed_count"],
            }
            json_results.append(json_r)
        
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "dataset": args.dataset,
            "num_questions": len(dataset),
            "modes_evaluated": args.modes,
            "config": {
                "top_k": TOP_K,
                "chunk_top_k": CHUNK_TOP_K,
                "judge_model": JUDGE_MODEL,
                "embedding_model": EMBEDDING_MODEL
            },
            "results": json_results
        }, f, indent=2)
    
    print(f"\n📁 Results saved: {json_path}")
    
    # Generate report
    report_path = RESULTS_DIR / f"report_{timestamp}.md"
    report = generate_markdown_report(all_results, report_path)
    print(f"📄 Report saved: {report_path}")
    
    # Print final summary
    print("\n" + "=" * 70)
    print("📊 FINAL SUMMARY")
    print("=" * 70)
    
    best_result = max(all_results, key=lambda x: x.get("ragas_score", 0))
    
    for result in all_results:
        mode = result["mode"]
        score = result.get("ragas_score", 0)
        marker = "👑" if mode == best_result["mode"] else "  "
        print(f"{marker} {mode:8}: RAGAS Score = {score:.4f}")
    
    print("=" * 70)
    print(f"🏆 Best Mode: {best_result['mode'].upper()} ({best_result['ragas_score']:.4f})")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
