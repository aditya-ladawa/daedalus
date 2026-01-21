"""LLM Configuration for Benchmark Agents.

Modify these values to change models without touching agent code.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# MAIN AGENT MODELS
# =============================================================================

# Deep Agent (Multi-agent orchestration)
DEEP_AGENT_MODEL = "deepseek-chat"
DEEP_AGENT_PROVIDER = "openai"  # Uses OpenAI-compatible API
DEEP_AGENT_BASE_URL = "https://api.deepseek.com"
DEEP_AGENT_TEMPERATURE = 0.0

# Alternative: Gemini 3 Pro
# DEEP_AGENT_MODEL = "gemini-3-pro-preview"
# DEEP_AGENT_PROVIDER = "google_genai"
# DEEP_AGENT_BASE_URL = None

# Basic Agent (Simple ReAct)
BASIC_AGENT_MODEL = "deepseek-chat"
BASIC_AGENT_PROVIDER = "openai"
BASIC_AGENT_BASE_URL = "https://api.deepseek.com"
BASIC_AGENT_TEMPERATURE = 0.0

# =============================================================================
# SUBAGENT MODELS (for deep agent)
# =============================================================================

SUBAGENT_MODEL = "gemini-2.5-flash"
SUBAGENT_PROVIDER = "google_genai"
SUBAGENT_TEMPERATURE = 0.0  # Deterministic for benchmark evaluation

# =============================================================================
# JUDGE MODELS (for evaluation)
# =============================================================================

JUDGE_MODEL = "gemini-2.5-flash"
JUDGE_PROVIDER = "google_genai"

# =============================================================================
# API KEYS
# =============================================================================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Validation
if not DEEPSEEK_API_KEY:
    import warnings
    warnings.warn("DEEPSEEK_API_KEY not found in environment variables")

if not GEMINI_API_KEY:
    import warnings
    warnings.warn("GEMINI_API_KEY not found in environment variables")

if not TAVILY_API_KEY:
    import warnings
    warnings.warn("TAVILY_API_KEY not found in environment variables")
