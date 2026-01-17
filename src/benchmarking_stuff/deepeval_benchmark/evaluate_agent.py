"""
DeepEval Agent Evaluation Script for Daedalus

Evaluates the Daedalus deep research agent using:
- 9 built-in DeepEval metrics (Action, Reasoning, RAG layers)
- 4 custom G-Eval metrics (Scientific, Structure, Citations, Isolation)

Usage:
    # Quick test (3 queries)
    python evaluate_agent.py --quick
    
    # Full evaluation (10 queries)
    python evaluate_agent.py
    
    # Single query test
    python evaluate_agent.py --query "Explain GWAS methodology"
    
    # Specific metrics only
    python evaluate_agent.py --metrics action reasoning
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv()

import config
from custom_metrics import get_all_custom_metrics

# DeepEval imports
try:
    from deepeval import evaluate
    from deepeval.test_case import LLMTestCase, ToolCall
    from deepeval.metrics import (
        # Core metrics (no context required)
        AnswerRelevancyMetric,
        # RAG Layer metrics (require retrieval_context)
        FaithfulnessMetric,
        HallucinationMetric,
        ContextualRelevancyMetric,
        # Action Layer metrics (require tools_called)
        TaskCompletionMetric,
        ToolCorrectnessMetric,
        ArgumentCorrectnessMetric,
        StepEfficiencyMetric,
        # Reasoning Layer metrics (require planning trace)
        PlanQualityMetric,
        PlanAdherenceMetric,
    )
    DEEPEVAL_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  DeepEval not fully installed: {e}")
    print("   Run: pip install deepeval")
    DEEPEVAL_AVAILABLE = False


# =============================================================================
# METRIC FACTORY
# =============================================================================

def get_builtin_metrics(categories: list = None, has_tools_called: bool = False) -> list:
    """
    Get built-in DeepEval metrics.
    
    Categories:
        - "core": AnswerRelevancy, Hallucination (no tools required, uses context from retrieval)
        - "action": TaskCompletion, ToolCorrectness, ArgumentCorrectness, StepEfficiency (requires tools_called)
        - "reasoning": PlanQuality, PlanAdherence (requires planning trace)
        - "rag": Faithfulness, ContextualRelevancy (requires retrieval_context)
    
    Args:
        categories: List of metric categories to include
        has_tools_called: If True, include action metrics that require tools_called
    """
    if categories is None:
        # Default: core metrics always, action+reasoning if tools, rag if no tools
        categories = ["core"]
        if has_tools_called:
            categories.extend(["action", "reasoning"])
        else:
            categories.append("rag")
    
    metrics = []
    
    # Core Layer - Always applicable (no special requirements)
    if "core" in categories:
        metrics.extend([
            AnswerRelevancyMetric(
                threshold=config.THRESHOLDS.get("answer_relevancy", 0.7),
                model=config.JUDGE_MODEL,
            ),
            HallucinationMetric(
                threshold=config.THRESHOLDS.get("hallucination", 0.7),
                model=config.JUDGE_MODEL,
            ),
        ])
    
    # Action Layer - Requires tools_called data
    if "action" in categories and has_tools_called:
        metrics.extend([
            TaskCompletionMetric(
                threshold=config.THRESHOLDS.get("task_completion", 0.7),
                model=config.JUDGE_MODEL,
            ),
            # NOTE: The following metrics have DeepEval library bugs - disabled for now
            # ToolCorrectnessMetric - requires expected_tools
            # ArgumentCorrectnessMetric - may have issues
            # StepEfficiencyMetric - UnboundLocalError in library
        ])
    
    # Reasoning Layer - Requires planning trace (todos)
    # NOTE: These metrics have DeepEval library bugs - disabled for now
    # if "reasoning" in categories and has_tools_called:
    #     metrics.extend([
    #         PlanQualityMetric(
    #             threshold=config.THRESHOLDS.get("plan_quality", 0.7),
    #             model=config.JUDGE_MODEL,
    #         ),
    #         PlanAdherenceMetric(
    #             threshold=config.THRESHOLDS.get("plan_adherence", 0.7),
    #             model=config.JUDGE_MODEL,
    #         ),
    #     ])
    
    # RAG Layer - Works with retrieval_context
    if "rag" in categories:
        metrics.extend([
            FaithfulnessMetric(
                threshold=config.THRESHOLDS.get("faithfulness", 0.7),
                model=config.JUDGE_MODEL,
            ),
            HallucinationMetric(
                threshold=config.THRESHOLDS.get("hallucination", 0.7),
                model=config.JUDGE_MODEL,
            ),
            ContextualRelevancyMetric(
                threshold=config.THRESHOLDS.get("contextual_relevancy", 0.7),
                model=config.JUDGE_MODEL,
            ),
        ])
    
    return metrics


def get_all_metrics(categories: list = None, include_custom: bool = True, has_tools_called: bool = False) -> list:
    """Get all metrics (built-in + custom)"""
    metrics = get_builtin_metrics(categories, has_tools_called=has_tools_called)
    
    if include_custom:
        metrics.extend(get_all_custom_metrics())
    
    return metrics


# =============================================================================
# TOOL EXTRACTION FROM AGENT MESSAGES
# =============================================================================

def extract_tool_calls(messages: list) -> list:
    """
    Extract ToolCall objects from LangGraph agent messages.
    
    Parses through AI messages with tool_calls and corresponding ToolMessages
    to build a list of DeepEval ToolCall objects.
    
    Args:
        messages: List of LangGraph messages from agent execution
    
    Returns:
        List of DeepEval ToolCall objects
    """
    tool_calls = []
    
    # Build a mapping of tool_call_id -> tool output
    tool_outputs = {}
    for msg in messages:
        # Check for ToolMessage (contains tool output)
        if hasattr(msg, 'type') and msg.type == 'tool':
            tool_call_id = getattr(msg, 'tool_call_id', None)
            if tool_call_id:
                tool_outputs[tool_call_id] = getattr(msg, 'content', '')
    
    # Extract tool calls from AI messages
    for msg in messages:
        if hasattr(msg, 'type') and msg.type == 'ai':
            # Check for tool_calls attribute
            msg_tool_calls = getattr(msg, 'tool_calls', [])
            if msg_tool_calls:
                for tc in msg_tool_calls:
                    tool_name = tc.get('name', 'unknown')
                    tool_args = tc.get('args', {})
                    tool_id = tc.get('id', '')
                    
                    # Get the output from matching ToolMessage
                    tool_output = tool_outputs.get(tool_id, '')
                    
                    # Create DeepEval ToolCall
                    tool_calls.append(ToolCall(
                        name=tool_name,
                        input_parameters=tool_args,
                        output=str(tool_output)[:2000] if tool_output else None,  # Truncate large outputs
                    ))
    
    return tool_calls


# =============================================================================
# EVALUATION FUNCTIONS
# =============================================================================

def evaluate_report(
    query: str,
    report_content: str,
    retrieval_context: list = None,
    tools_called: list = None,
    metrics: list = None,
) -> dict:
    """
    Evaluate a single research report.
    
    Args:
        query: The original research question
        report_content: The generated report text
        retrieval_context: Optional list of retrieved context strings (for RAG metrics)
        tools_called: Optional list of ToolCall objects (for action metrics)
        metrics: Optional list of metrics to use (defaults to all)
    
    Returns:
        Dict with scores for each metric
    """
    if metrics is None:
        metrics = get_all_metrics(has_tools_called=bool(tools_called))
    
    # Create test case with tools_called if available
    # NOTE: Both 'context' and 'retrieval_context' must be provided for RAG metrics
    # - context: ground truth context (for HallucinationMetric)
    # - retrieval_context: actual retrieved context (for FaithfulnessMetric)
    test_case_kwargs = {
        "input": query,
        "actual_output": report_content,
        "context": retrieval_context or [],  # Required for HallucinationMetric
        "retrieval_context": retrieval_context or [],  # Required for FaithfulnessMetric
    }
    
    if tools_called:
        test_case_kwargs["tools_called"] = tools_called
    
    test_case = LLMTestCase(**test_case_kwargs)
    
    # Run evaluation
    evaluation_result = evaluate(
        test_cases=[test_case],
        metrics=metrics,
    )
    
    # Extract scores from EvaluationResult
    # evaluate() returns EvaluationResult with test_results: List[TestResult]
    # Each TestResult has metrics_data: List[MetricData]
    scores = {}
    
    if evaluation_result.test_results and len(evaluation_result.test_results) > 0:
        test_result = evaluation_result.test_results[0]
        if test_result.metrics_data:
            for metric_data in test_result.metrics_data:
                scores[metric_data.name] = {
                    "score": metric_data.score,
                    "reason": metric_data.reason,
                    "passed": metric_data.success,
                    "threshold": metric_data.threshold,
                    "error": metric_data.error,
                }
    
    # Fallback: if no results extracted, try from metric objects (legacy behavior)
    if not scores:
        for metric in metrics:
            metric_name = getattr(metric, 'name', metric.__class__.__name__)
            scores[metric_name] = {
                "score": getattr(metric, 'score', None),
                "reason": getattr(metric, 'reason', None),
                "passed": metric.is_successful() if hasattr(metric, 'is_successful') else None,
                "threshold": getattr(metric, 'threshold', None),
                "error": getattr(metric, 'error', None),
            }
    
    return {
        "query": query,
        "scores": scores,
        "overall_pass": all(
            s.get("passed", True) for s in scores.values() if s.get("passed") is not None
        ),
    }


async def evaluate_with_daedalus(
    query: str,
    metrics: list = None,
    output_dir: Path = None,
) -> dict:
    """
    Run Daedalus agent on a query and evaluate the output.
    
    Args:
        query: The research question
        metrics: Optional list of metrics to use
        output_dir: Directory to save agent output (defaults to agent_workspace/eval_runs/)
    
    Returns:
        Evaluation results dict
    """
    print(f"\n{'='*60}")
    print(f"📝 Query: {query[:80]}...")
    print("="*60)
    
    # Setup output directory
    if output_dir is None:
        output_dir = PROJECT_ROOT / "agent_workspace" / "eval_runs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Import the Daedalus agent graph
    try:
        from agent_graph.graph import graph
        print("  ✅ Loaded Daedalus agent graph")
    except ImportError as e:
        print(f"  ❌ Could not import agent graph: {e}")
        return {
            "query": query,
            "scores": {},
            "overall_pass": False,
            "error": str(e),
        }
    
    # Run the agent
    print("  🤖 Running Daedalus agent...")
    start_time = datetime.now()
    
    try:
        # For evaluation, explicitly request a comprehensive report
        # This ensures the agent produces full reports with sections and citations
        evaluation_query = f"Write a comprehensive research report on: {query}"
        
        # Invoke the agent with the query
        result = await graph.ainvoke({
            "messages": [{"role": "user", "content": evaluation_query}]
        })
        
        # Extract agent output from messages
        messages = result.get("messages", [])
        if messages:
            # Get the last assistant message
            agent_output = ""
            for msg in reversed(messages):
                if hasattr(msg, "content") and hasattr(msg, "type"):
                    if msg.type == "ai":
                        agent_output = msg.content
                        break
                elif isinstance(msg, dict) and msg.get("role") == "assistant":
                    agent_output = msg.get("content", "")
                    break
            
            if not agent_output:
                # Fallback: concatenate all assistant messages
                agent_output = "\n\n".join([
                    m.content for m in messages 
                    if hasattr(m, "content") and hasattr(m, "type") and m.type == "ai"
                ])
        else:
            agent_output = "[No output from agent]"
        
        # Ensure report_content is a string (handle multimodal/list content)
        if isinstance(agent_output, list):
            # Handle multimodal content (list of content blocks)
            parts = []
            for part in agent_output:
                if isinstance(part, dict) and 'text' in part:
                    parts.append(part['text'])
                elif isinstance(part, str):
                    parts.append(part)
                else:
                    parts.append(str(part))
            report_content = "\n".join(parts)
        elif agent_output is None:
            report_content = ""
        else:
            report_content = str(agent_output)
        
        # CRITICAL: If agent response is just meta-commentary, extract actual written content
        # Check if response is likely meta-commentary (short or contains common patterns)
        meta_patterns = [
            "I've saved", "I have saved", "saved to", 
            "Now let me", "I will now", "I'll create",
            "has been generated", "report has been",
            "created the", "writing the", "Citation Registry"
        ]
        is_meta_commentary = (
            len(report_content) < 500 or
            any(pattern.lower() in report_content.lower() for pattern in meta_patterns) or
            report_content.strip().startswith("# Citation Registry")
        )
        
        # Extract tool calls for agentic evaluation
        tools_called = extract_tool_calls(messages)
        
        # If the response is meta-commentary, try to get actual content from write_file calls
        if is_meta_commentary:
            written_files = []
            for tc in tools_called:
                # Look for write_file or edit_file tool calls
                if tc.name in ['write_file', 'edit_file']:
                    # The tool arguments should contain the content
                    if tc.input_parameters:
                        file_path = tc.input_parameters.get('path', '')
                        content = tc.input_parameters.get('content', '')
                        
                        # Skip references.md - we want the actual report
                        if 'references.md' in file_path.lower():
                            continue
                        
                        # Only include substantial content files
                        if content and len(content) > 200:
                            written_files.append({
                                'path': file_path,
                                'content': content,
                                'size': len(content)
                            })
            
            # If we found written content, use the largest file (likely the report)
            if written_files:
                # Sort by size, largest first
                written_files.sort(key=lambda x: x['size'], reverse=True)
                largest_file = written_files[0]
                
                if largest_file['size'] > len(report_content):
                    report_content = largest_file['content']
                    print(f"  ⚠️  Agent returned meta-commentary/references. Using written file content instead: {largest_file['path']} ({largest_file['size']} chars)")
        
        # =================================================================
        # PRIMARY FILE EXTRACTION: Always read from agent_workspace/ disk
        # This is the most reliable method - directly read the written files
        # =================================================================
        from pathlib import Path
        import time
        import re
        
        agent_workspace = Path(__file__).parent.parent.parent.parent / "agent_workspace"
        
        # Try to extract file paths mentioned in agent's response
        mentioned_paths = []
        path_patterns = [
            r'saved to[:\s]+([a-zA-Z0-9_/]+\.md)',
            r'written to[:\s]+([a-zA-Z0-9_/]+\.md)',
            r'report\.md',
            r'([a-zA-Z0-9_]+/report\.md)',
        ]
        for pattern in path_patterns:
            matches = re.findall(pattern, report_content, re.IGNORECASE)
            mentioned_paths.extend(matches)
        
        # Also check tool call outputs for file paths
        for tc in tools_called:
            if tc.name == 'write_file' and tc.input_parameters:
                path = tc.input_parameters.get('path', '')
                if path and path.endswith('.md') and 'references' not in path.lower():
                    mentioned_paths.append(path)
        
        if agent_workspace.exists():
            current_time = time.time()
            all_report_files = []
            
            # First, try to find explicitly mentioned files
            for mentioned_path in mentioned_paths:
                # Try various path combinations
                possible_paths = [
                    agent_workspace / mentioned_path,
                    agent_workspace / mentioned_path.lstrip('/'),
                ]
                for p in possible_paths:
                    if p.exists() and p.is_file():
                        try:
                            content = p.read_text(encoding='utf-8')
                            if len(content) > 500:
                                all_report_files.append({
                                    'path': str(p),
                                    'content': content,
                                    'size': len(content),
                                    'mentioned': True,
                                    'age': current_time - p.stat().st_mtime
                                })
                        except Exception:
                            pass
            
            # Also scan for recent report files
            for md_file in agent_workspace.rglob("*.md"):
                # Skip references.md
                if "references.md" in str(md_file).lower():
                    continue
                    
                try:
                    file_stat = md_file.stat()
                    file_age_seconds = current_time - file_stat.st_mtime
                    
                    # File modified in last 30 minutes (more generous window)
                    if file_age_seconds < 1800:
                        content = md_file.read_text(encoding='utf-8')
                        # Must have substantial content
                        if len(content) > 1000:
                            # Prefer files named "report.md"
                            is_report = 'report.md' in str(md_file).lower()
                            all_report_files.append({
                                'path': str(md_file),
                                'content': content,
                                'size': len(content),
                                'mentioned': False,
                                'is_report': is_report,
                                'age': file_age_seconds
                            })
                except Exception as e:
                    pass  # Silently skip unreadable files
            
            if all_report_files:
                # Sort priority: mentioned > is_report > size > recency
                def sort_key(f):
                    return (
                        -int(f.get('mentioned', False)),  # Mentioned files first
                        -int(f.get('is_report', False)),  # report.md files next
                        -f['size'],                        # Larger files next
                        f['age']                           # Most recent next
                    )
                all_report_files.sort(key=sort_key)
                best_file = all_report_files[0]
                
                # Always use the disk file if it's larger than what we have
                if best_file['size'] > len(report_content) or len(report_content) < 2000:
                    report_content = best_file['content']
                    print(f"  📄 Using report from disk: {best_file['path']} ({best_file['size']} chars)")
        
        
        
        
        # Extract retrieval context from tool outputs for RAG metrics
        # Filter out error messages and stack traces
        retrieval_context = []
        for tc in tools_called:
            if tc.output and len(str(tc.output)) > 50:
                output_str = str(tc.output)
                # Skip if it's an error message or stack trace
                if any(error_indicator in output_str for error_indicator in [
                    'Error executing',
                    'Traceback',
                    'Exception:',
                    'Failed to',
                    'socket.gaierror',
                    'ConnectionError',
                ]):
                    continue
                # Skip if it's just todo list updates (not actual research content)
                if output_str.startswith('Updated todo list to'):
                    continue
                # Skip agent meta-commentary
                if any(meta_phrase in output_str for meta_phrase in [
                    'I have gathered',
                    'I will now',
                    'Synthesize findings into',
                    'Based on the search results',
                ]):
                    continue
                retrieval_context.append(output_str)
        
        # Ensure we have at least some context for metrics
        if not retrieval_context:
            retrieval_context = ["No additional context was retrieved by the agent during this run."]
        
    except Exception as e:
        print(f"  ❌ Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "query": query,
            "scores": {},
            "overall_pass": False,
            "error": str(e),
        }
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"  ⏱️  Agent completed in {elapsed:.1f}s")
    print(f"  📄 Output length: {len(report_content)} chars")
    print(f"  🔧 Tool calls captured: {len(tools_called)}")
    print(f"  📚 Retrieval context items: {len(retrieval_context)}")
    
    # Save output for reference
    safe_query = "".join(c if c.isalnum() or c in " -_" else "" for c in query[:50])
    output_file = output_dir / f"eval_{safe_query.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}.md"
    with open(output_file, "w") as f:
        f.write(f"# Query\n{query}\n\n# Agent Output\n{report_content}")
        f.write(f"\n\n# Tool Calls ({len(tools_called)})\n")
        for tc in tools_called:
            f.write(f"- {tc.name}: {tc.input_parameters}\n")
    print(f"  💾 Saved to: {output_file.name}")
    
    # Evaluate with DeepEval
    print("  🔍 Evaluating with DeepEval...")
    
    result = evaluate_report(
        query=query,
        report_content=report_content,
        retrieval_context=retrieval_context,
        tools_called=tools_called if tools_called else None,
        metrics=metrics,
    )
    
    # Print summary
    print(f"\n  📊 Results:")
    for name, data in result["scores"].items():
        score = data.get("score", 0) or 0
        passed = "✅" if data.get("passed", False) else "❌"
        print(f"    {passed} {name}: {score:.2f}")
    
    return result


async def run_evaluation(
    queries: list = None,
    categories: list = None,
    include_custom: bool = True,
    quick: bool = False,
) -> list:
    """
    Run full evaluation on multiple queries.
    
    Args:
        queries: List of query strings (defaults to config.TEST_QUERIES)
        categories: Metric categories to include ("action", "reasoning", "rag")
        include_custom: Whether to include custom G-Eval metrics
        quick: If True, only run on first 3 queries
    
    Returns:
        List of evaluation results
    """
    if queries is None:
        queries = config.TEST_QUERIES
    
    if quick:
        queries = queries[:config.QUICK_TEST_COUNT]
    
    # Get metrics - Daedalus always uses tools, so include agentic metrics
    metrics = get_all_metrics(categories, include_custom, has_tools_called=True)
    
    print("\n" + "="*70)
    print("🔬 DeepEval Agent Benchmark")
    print("="*70)
    config.print_config()
    print(f"\n📋 Queries: {len(queries)}")
    print(f"📊 Metrics: {len(metrics)}")
    for m in metrics:
        metric_name = getattr(m, 'name', m.__class__.__name__)
        print(f"    - {metric_name}")
    print("="*70)
    
    results = []
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Processing...")
        result = await evaluate_with_daedalus(query, metrics=metrics)
        results.append(result)
    
    return results


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(results: list, output_path: Path = None) -> str:
    """Generate markdown report from evaluation results"""
    
    lines = [
        "# DeepEval Agent Benchmark Results",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Judge Model:** {config.JUDGE_MODEL}",
        f"**Queries Evaluated:** {len(results)}",
        "",
        "---",
        "",
        "## Summary",
        "",
    ]
    
    # Calculate averages
    all_scores = {}
    for result in results:
        for metric_name, data in result["scores"].items():
            if metric_name not in all_scores:
                all_scores[metric_name] = []
            if data.get("score") is not None:
                all_scores[metric_name].append(data["score"])
    
    lines.append("| Metric | Avg Score | Pass Rate |")
    lines.append("|--------|-----------|-----------|")
    
    for metric_name, scores in all_scores.items():
        avg = sum(scores) / len(scores) if scores else 0
        threshold = config.THRESHOLDS.get(metric_name, config.DEFAULT_THRESHOLD)
        pass_count = sum(1 for s in scores if s >= threshold)
        pass_rate = pass_count / len(scores) * 100 if scores else 0
        lines.append(f"| {metric_name} | {avg:.2f} | {pass_rate:.0f}% |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Per-Query Results",
        "",
    ])
    
    for i, result in enumerate(results, 1):
        query = result["query"]
        overall = "✅ PASS" if result["overall_pass"] else "❌ FAIL"
        
        lines.append(f"### Query {i}")
        lines.append(f"**{query}**")
        lines.append(f"**Overall:** {overall}")
        lines.append("")
        lines.append("| Metric | Score | Passed | Reason |")
        lines.append("|--------|-------|--------|--------|")
        
        for metric_name, data in result["scores"].items():
            score = data.get("score", 0) or 0
            passed = "✅" if data.get("passed", False) else "❌"
            reason = (data.get("reason", "") or "").replace("|", "/").replace("\n", " ")
            lines.append(f"| {metric_name} | {score:.2f} | {passed} | {reason} |")
        
        lines.append("")
    
    report = "\n".join(lines)
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
    
    return report


def save_results(results: list) -> tuple:
    """Save results to JSON and Markdown"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON
    json_path = config.RESULTS_DIR / f"evaluation_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": {
                "judge_model": config.JUDGE_MODEL,
                "thresholds": config.THRESHOLDS,
            },
            "results": results,
        }, f, indent=2, default=str)
    
    # Markdown
    md_path = config.RESULTS_DIR / f"report_{timestamp}.md"
    generate_report(results, md_path)
    
    return json_path, md_path


# =============================================================================
# CLI
# =============================================================================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DeepEval Benchmark for Daedalus Agent"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help=f"Quick test with {config.QUICK_TEST_COUNT} queries"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Evaluate a single query"
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        choices=["action", "reasoning", "rag", "custom"],
        default=None,
        help="Metric categories to include"
    )
    parser.add_argument(
        "--no-custom",
        action="store_true",
        help="Exclude custom G-Eval metrics"
    )
    parser.add_argument(
        "--report-only",
        type=str,
        help="Generate report from existing JSON results file"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    if not DEEPEVAL_AVAILABLE:
        print("❌ DeepEval not available. Please install required packages.")
        return
    
    # Report only mode
    if args.report_only:
        with open(args.report_only, 'r') as f:
            data = json.load(f)
        report = generate_report(data["results"])
        print(report)
        return
    
    # Determine metric categories
    categories = args.metrics
    if categories and "custom" in categories:
        categories = [c for c in categories if c != "custom"]
        include_custom = True
    else:
        include_custom = not args.no_custom
    
    # Single query mode
    if args.query:
        metrics = get_all_metrics(categories, include_custom, has_tools_called=True)
        result = await evaluate_with_daedalus(args.query, metrics=metrics)
        
        # Save single result
        json_path, md_path = save_results([result])
        print(f"\n📁 JSON saved: {json_path}")
        print(f"📄 Report saved: {md_path}")
        
        # Print summary to console as well
        print("\n" + "="*80)
        print("  📊 Results:")
        for metric_name, data in result["scores"].items():
            reason = (data.get("reason", "") or "").replace("\n", " ")
            icon = "✅" if data.get("passed") else "❌"
            print(f"    {icon} {metric_name}: {data.get('score', 0):.2f}")
            print(f"       Reason: {reason}")
        print(json.dumps(result, indent=2, default=str))
        return
    
    # Full evaluation
    results = await run_evaluation(
        categories=categories,
        include_custom=include_custom,
        quick=args.quick,
    )
    
    # Save results
    json_path, md_path = save_results(results)
    print(f"\n📁 JSON saved: {json_path}")
    print(f"📄 Report saved: {md_path}")
    
    # Print summary
    print("\n" + "="*70)
    print("📊 EVALUATION COMPLETE")
    print("="*70)
    
    pass_count = sum(1 for r in results if r["overall_pass"])
    print(f"✅ Passed: {pass_count}/{len(results)}")
    print(f"❌ Failed: {len(results) - pass_count}/{len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
