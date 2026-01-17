"""
DeepEval Tracing Configuration

This module provides the @observe decorator for DeepEval tracing.
Tracing can be enabled/disabled via environment variable DEEPEVAL_TRACING=true/false.

Usage:
    from agent_graph.tracing import observe, update_trace

    @observe(type="agent", name="my_agent")
    async def my_agent_function():
        ...

    @observe(type="tool", name="my_tool")
    def my_tool_function():
        ...
"""

import os
from functools import wraps
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Check if DeepEval tracing is enabled
TRACING_ENABLED = os.environ.get("DEEPEVAL_TRACING", "false").lower() == "true"

# Try to import DeepEval's observe decorator
try:
    from deepeval.tracing import observe as deepeval_observe
    from deepeval.tracing import update_current_span, update_current_trace
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False
    deepeval_observe = None
    update_current_span = None
    update_current_trace = None


def observe(type: str = None, name: str = None, metrics: list = None):
    """
    Decorator for DeepEval tracing. Falls back to no-op if DeepEval not installed or tracing disabled.
    
    Args:
        type: Component type - "agent", "tool", "llm", "retriever"
        name: Name of the component for tracing (optional, uses function name if not provided)
        metrics: Optional list of metrics to evaluate on this component
    
    Example:
        @observe(type="agent", name="daedalus_main_agent")
        async def run_agent(query: str):
            ...
        
        @observe(type="tool", name="search_research_papers")
        def search_papers(query: str, mode: str):
            ...
    
    Note: DeepEval automatically uses the decorated function's __name__ as the span name.
    The 'name' parameter here is for documentation but DeepEval extracts name from the function.
    """
    def decorator(func):
        # If tracing is disabled or DeepEval not available, return original function
        if not TRACING_ENABLED or not DEEPEVAL_AVAILABLE:
            return func
        
        # Handle case where func is already a LangChain StructuredTool
        # In this case, we can't apply @observe (it needs a raw function)
        # Just return the tool as-is
        if hasattr(func, 'name') and not hasattr(func, '__name__'):
            # This is likely a StructuredTool or similar wrapper
            # Skip tracing for this one
            return func
        
        # Apply DeepEval's observe decorator
        # Note: DeepEval uses function.__name__ as the span name automatically
        # We only pass 'type' and optionally 'metrics'
        try:
            if metrics:
                return deepeval_observe(type=type, metrics=metrics)(func)
            else:
                return deepeval_observe(type=type)(func)
        except Exception as e:
            # On any error, fall back to undecorated function
            func_name = getattr(func, '__name__', getattr(func, 'name', repr(func)))
            print(f"⚠️ Could not apply @observe to {func_name}: {e}")
            return func
    
    return decorator


def update_span(**kwargs):
    """Update the current span with additional data (e.g., tools_called)."""
    if TRACING_ENABLED and DEEPEVAL_AVAILABLE and update_current_span:
        update_current_span(**kwargs)


def update_trace(**kwargs):
    """Update the current trace with additional data."""
    if TRACING_ENABLED and DEEPEVAL_AVAILABLE and update_current_trace:
        update_current_trace(**kwargs)


def is_tracing_enabled() -> bool:
    """Check if tracing is currently enabled."""
    return TRACING_ENABLED and DEEPEVAL_AVAILABLE


def print_tracing_status():
    """Print current tracing configuration."""
    print("=" * 60)
    print("📊 DeepEval Tracing Configuration")
    print("=" * 60)
    print(f"  Environment DEEPEVAL_TRACING: {os.environ.get('DEEPEVAL_TRACING', 'not set')}")
    print(f"  Tracing Enabled: {TRACING_ENABLED}")
    print(f"  DeepEval Available: {DEEPEVAL_AVAILABLE}")
    print(f"  Status: {'✅ Active' if is_tracing_enabled() else '❌ Inactive'}")
    print("=" * 60)
    
    if not DEEPEVAL_AVAILABLE:
        print("  💡 To enable tracing: pip install deepeval")
    elif not TRACING_ENABLED:
        print("  💡 To enable tracing: export DEEPEVAL_TRACING=true")


if __name__ == "__main__":
    print_tracing_status()
    
    # Test decorator
    @observe(type="tool", name="test_tool")
    def test_function(x):
        return f"Hello {x}"
    
    result = test_function("World")
    print(f"\nTest function result: {result}")
    print("✅ Tracing module works correctly")
