"""
Configuration for DeepEval Benchmark

Configurable judge LLM settings. Swap these to change the evaluation model.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Increase DeepEval timeout for large context evaluations
os.environ["DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE"] = "300"

# =============================================================================
# JUDGE LLM CONFIGURATION
# =============================================================================

# Model for LLM-as-Judge evaluations
# Options: 
#   - "gemini/gemini-2.5-flash" (recommended)
#   - "gemini/gemini-2.5-pro" (more capable)
#   - "gpt-4o" (OpenAI)
#   - "gpt-4o-mini" (OpenAI cheaper)
_MODEL_NAME = "gemini/gemini-2.5-pro"

# Gemini-specific settings
GEMINI_THINKING_LEVEL = "minimal"  # Options: "none", "minimal", "standard", "deep"

# Model temperature for evaluations (0 = deterministic)
JUDGE_TEMPERATURE = 0

# Instantiate model object for Gemini
if _MODEL_NAME.startswith("gemini/"):
    from deepeval.models.llms.gemini_model import GeminiModel
    # Strip "gemini/" prefix as GeminiModel expects just the model ID
    _actual_model_name = _MODEL_NAME.split("/", 1)[1]
    
    # Get API key specifically for Gemini
    _gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not _gemini_key:
        print("⚠️  Warning: GEMINI_API_KEY or GOOGLE_API_KEY not found in environment")
        
    JUDGE_MODEL = GeminiModel(model=_actual_model_name, api_key=_gemini_key, temperature=JUDGE_TEMPERATURE)
else:
    # DeepEval treats strings as OpenAI models by default
    JUDGE_MODEL = _MODEL_NAME

# =============================================================================
# METRIC THRESHOLDS
# =============================================================================

# Default threshold for passing (0.0 to 1.0)
DEFAULT_THRESHOLD = 0.7

# Per-metric thresholds (override defaults if needed)
THRESHOLDS = {
    # Core Layer
    "answer_relevancy": 0.7,
    
    # Action Layer
    "task_completion": 0.7,
    "tool_correctness": 0.7,
    "argument_correctness": 0.7,
    "step_efficiency": 0.5,  # Lower threshold - efficiency is bonus
    
    # Reasoning Layer
    "plan_quality": 0.7,
    "plan_adherence": 0.7,
    
    # RAG Layer
    "faithfulness": 0.7,
    "hallucination": 0.7,
    "contextual_relevancy": 0.7,
    
    # Custom Metrics
    "scientific_precision": 0.7,
    "section_coherence": 0.7,
    "citation_quality": 0.7,
    "isolation_effectiveness": 0.7,
    "research_depth": 0.7,
}

# =============================================================================
# PATHS
# =============================================================================

# Directory for this benchmark
BENCHMARK_DIR = Path(__file__).parent

# Results directory
RESULTS_DIR = BENCHMARK_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Project root
PROJECT_ROOT = BENCHMARK_DIR.parent.parent.parent

# =============================================================================
# API KEYS (loaded from environment)
# =============================================================================

def get_api_key():
    """Get the appropriate API key based on judge model"""
    if _MODEL_NAME.startswith("gemini/"):
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set")
        return key
    elif _MODEL_NAME.startswith("gpt-"):
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY must be set")
        return key
    else:
        raise ValueError(f"Unknown model provider: {_MODEL_NAME}")


# =============================================================================
# EVALUATION SETTINGS
# =============================================================================

# Number of test queries for quick evaluation
QUICK_TEST_COUNT = 3

# Full test queries
TEST_QUERIES = [
    "Explain the genetic architecture of alcohol use disorder",
    "What are the cross-ancestry findings for depression GWAS?",
    "Describe pathway-based polygenic risk scores and their advantages",
    "Compare GWAS findings between males and females for substance use disorders",
    "Explain the role of ALDH2 and ADH1B in alcohol metabolism",
    "What is the heritability of major depressive disorder?",
    "Describe the methodology of genome-wide association studies",
    "What are polygenic risk scores and how are they calculated?",
    "Explain gene-environment interactions in psychiatric genetics",
    "What are the limitations of current GWAS studies?",
]

# =============================================================================
# DISPLAY
# =============================================================================

def print_config():
    """Print current configuration"""
    model_name = JUDGE_MODEL.get_model_name() if hasattr(JUDGE_MODEL, 'get_model_name') else str(JUDGE_MODEL)
    print("=" * 60)
    print("🔧 DeepEval Benchmark Configuration")
    print("=" * 60)
    print(f"  Judge Model: {model_name}")
    print(f"  Thinking Level: {GEMINI_THINKING_LEVEL}")
    print(f"  Temperature: {JUDGE_TEMPERATURE}")
    print(f"  Default Threshold: {DEFAULT_THRESHOLD}")
    print(f"  Results Dir: {RESULTS_DIR}")
    print("=" * 60)
