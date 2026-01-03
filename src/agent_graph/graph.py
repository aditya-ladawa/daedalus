"""Deep Research Agent using LangGraph's create_react_agent.

This module builds the main orchestrator agent and its specialized sub-agents
for long-running research tasks.
"""

from datetime import UTC, datetime

from langgraph.prebuilt import create_react_agent

from agent_graph.context import Context
from agent_graph.state import DeepAgentState, InputState
from agent_graph.tools import TOOLS, create_task_delegation_tool
from agent_graph.utils import load_chat_model
from agent_graph import prompts


def _build_agent_graph():
    """Build the deep research agent graph with lazy initialization.
    
    This function creates the main orchestrator agent using create_react_agent.
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
    # Load default models
    default_main_model = load_chat_model("google_genai/gemini-3-pro-preview")
    default_subagent_model = load_chat_model("google_genai/gemini-3-flash-preview")
    
    # Create task delegation tool with default sub-agent model
    task_tool = create_task_delegation_tool(default_subagent_model)
    
    # Main agent tools: orchestration only (delegation + state management)
    main_agent_tools = TOOLS + [task_tool]
    
    print("🧠 Building Deep Research Agent...")
    print(f"  Main Agent: {len(main_agent_tools)} tools (orchestration only)")
    print(f"    - Model: google_genai/gemini-3-flash-preview")
    print("  Sub-agents:")
    print("    - internet_researcher: Web search specialist")
    print("      Model: google_genai/gemini-3-flash-preview")
    print("    - file_manager: File operations specialist")
    print("      Model: google_genai/gemini-3-flash-preview")
    
    # Create the main agent using create_react_agent
    graph = create_react_agent(
        default_main_model,
        tools=main_agent_tools,
        state_schema=DeepAgentState,
        prompt=prompts.SYSTEM_PROMPT
    )
    
    print("✅ Deep Research Agent ready!")
    return graph


# Build the agent graph
# Note: This runs at module import time, which is required by LangGraph
graph = _build_agent_graph()

__all__ = ["graph"]
