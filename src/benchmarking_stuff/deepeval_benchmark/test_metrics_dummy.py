"""
Dummy Test for DeepEval Metrics

Verify that the DeepEval + Gemini integration is working correctly.
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "benchmarking_stuff" / "deepeval_benchmark"))

import config

from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import HallucinationMetric, FaithfulnessMetric

def test_dummy_metric():
    model_name = config.JUDGE_MODEL.get_model_name() if hasattr(config.JUDGE_MODEL, 'get_model_name') else str(config.JUDGE_MODEL)
    print(f"Testing Metrics with Judge: {model_name}")
    
    # Simple test case
    context = ["Paris is the capital of France."]
    input_text = "What is the capital of France?"
    actual_output = "The capital of France is Paris."
    
    test_case = LLMTestCase(
        input=input_text,
        actual_output=actual_output,
        context=context,
        retrieval_context=context
    )
    
    metrics = [
        HallucinationMetric(threshold=0.5, model=config.JUDGE_MODEL),
        FaithfulnessMetric(threshold=0.5, model=config.JUDGE_MODEL)
    ]
    
    print("Running evaluate...")
    try:
        evaluation_result = evaluate(
            test_cases=[test_case],
            metrics=metrics,
        )
        print("\n✅ Evaluation completed successfully!")
        
        # Extract scores from EvaluationResult
        if evaluation_result.test_results and len(evaluation_result.test_results) > 0:
            test_result = evaluation_result.test_results[0]
            print(f"\nTest Result: {'PASSED' if test_result.success else 'FAILED'}")
            
            if test_result.metrics_data:
                print("\nMetric Results:")
                for metric_data in test_result.metrics_data:
                    status = "✅" if metric_data.success else "❌"
                    print(f"  {status} {metric_data.name}:")
                    print(f"      Score: {metric_data.score}")
                    print(f"      Threshold: {metric_data.threshold}")
                    print(f"      Reason: {metric_data.reason}")
                    if metric_data.error:
                        print(f"      Error: {metric_data.error}")
                        
    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dummy_metric()
