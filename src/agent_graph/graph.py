"""Deep Research Agent using LangGraph's create_react_agent.

This module builds the main orchestrator agent and its specialized sub-agents
for long-running research tasks. Models are configured via context.py for
runtime selection in LangGraph Studio.
"""

from datetime import UTC, datetime

from langgraph.prebuilt import create_react_agent
from langgraph.runtime import Runtime

from agent_graph.context import Context
from agent_graph.state import DeepAgentState, InputState
from agent_graph.tools import TOOLS, create_task_delegation_tool
from agent_graph.utils import load_chat_model
from agent_graph import prompts


def _build_agent_graph():
    """Build the deep research agent graph with runtime configuration.
    
    This function creates the main orchestrator agent using create_react_agent.
    Models are loaded from Runtime[Context] at execution time, which can be 
    configured via LangGraph Studio's Assistants feature.
    
    The main agent has access to:
    - Task delegation tool (for spawning sub-agents)
    - Todo management tools (read_todos, write_todos)
    - Strategic thinking tool (think_strategically)
    
    Sub-agents are created dynamically by the task delegation tool with:
    - internet_researcher: Web search specialist
    - file_manager: File operations specialist (bash-based)
    
    Returns:
        Compiled LangGraph agent ready for execution
    """
    # Use default context for initialization
    # Runtime context will be injected via Runtime[Context] in tools
    ctx = Context()
    
    # Load default models (will be overridden at runtime via Runtime[Context])
    main_model = load_chat_model(ctx.model)
    subagent_model = load_chat_model(ctx.subagent_model)
    
    # Create task delegation tool
    # Models will be loaded from runtime context in the tool execution
    task_tool = create_task_delegation_tool(
        model=subagent_model,
        researcher_model=subagent_model
    )
    
    # Main agent tools: orchestration only (delegation + state management)
    main_agent_tools = TOOLS + [task_tool]
    
    print("🧠 Building Deep Research Agent...")
    print(f"  Main Agent: {len(main_agent_tools)} tools (orchestration only)")
    print(f"    - Model: {ctx.model} (configurable via Studio)")
    print("  Sub-agents:")
    print(f"    - internet_researcher: Web search specialist")
    print(f"      Model: {ctx.subagent_model} (configurable via Studio)")
    print(f"    - file_manager: File operations specialist")
    print(f"      Model: {ctx.subagent_model} (configurable via Studio)")
    
    # Create the main agent using create_react_agent
    graph = create_react_agent(
        main_model,
        tools=main_agent_tools,
        state_schema=DeepAgentState,
        prompt=ctx.system_prompt
    )
    
    print("✅ Deep Research Agent ready!")
    return graph


# Build the agent graph
# Note: This runs at module import time for LangGraph
# Runtime configuration happens via Runtime[Context] injection
graph = _build_agent_graph()

__all__ = ["graph"]
