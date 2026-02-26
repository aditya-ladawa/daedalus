"""Deep Research Agent using LangGraph's create_react_agent.

This module builds the main orchestrator agent and its specialized sub-agents
for long-running research tasks. Models are configured via context.py for
runtime selection in LangGraph Studio.
"""

from datetime import UTC, datetime

from langgraph.prebuilt import create_react_agent
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig

from agent_graph.context import Context
from agent_graph.state import DeepAgentState, InputState
from agent_graph.tools import TOOLS, create_task_delegation_tool
from agent_graph.utils import load_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from agent_graph import prompts
import os


llm = ChatOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "n/a"),
    base_url="https://openrouter.ai/api/v1",
    model="moonshotai/kimi-k2.5",
    extra_body={"thinking": {"type": "disabled"}},
    max_retries=5,
    request_timeout=120,
)

# llm = ChatOpenAI(
#     api_key=os.environ.get("DEEPSEEK_API_KEY", "n/a"),
#     base_url="https://api.deepseek.com",
#     model="deepseek-chat",
#     # extra_body={"thinking": {"type": "disabled"}},
#     max_retries=5,
#     request_timeout=120,
# )

# llm = ChatGoogleGenerativeAI(
#     api_key=os.environ.get("GEMINI_API_KEY", "n/a"),
#     model="gemini-3.1-pro-preview",
#     max_retries=5,
#     request_timeout=120,
# )

def _build_agent_graph():
    """Build the deep research agent graph with runtime configuration.
    
    This function creates the main orchestrator agent using create_react_agent.
    Models are loaded from Runtime[Context] at execution time, which can be 
    configured via LangGraph Studio's Assistants feature.
    
    The main agent has access to:
    - Task delegation tool (for spawning sub-agents)
    - Todo management tools (read_todos, write_todos)
    - Strategic thinking tool (think_strategically)
    - Write tools (write_file, edit_file) for direct file operations
    
    Sub-agents are created dynamically by the task delegation tool with:
    - internet_researcher: Web search specialist
    - filesystem_reader: File system reader (read-only context gathering)
    - script_executor: Script execution specialist (bash, PDF conversion)
    - biomedical_researcher: RAG knowledge base specialist
    
    Returns:
        Compiled LangGraph agent ready for execution
    """
    # Use default context for initialization
    # Runtime context will be injected via Runtime[Context] in tools
    ctx = Context()
    
    # Load default models (will be overridden at runtime via Runtime[Context])
    # main_model = load_chat_model(ctx.model)
    main_model = llm
    
    # # Configure thinking level for gemini-2.0-flash-thinking-exp
    # if "gemini-3-flash-preview" in ctx.model:
    #     main_model = main_model.bind(thinking_level="minimal")
    
    # # Set max output tokens for comprehensive research papers
    # main_model = main_model.bind(max_tokens=16384, temperature=0.3)
    
    # subagent_model = load_chat_model(ctx.subagent_model)
    subagent_model = llm
#     subagent_model = ChatGoogleGenerativeAI(
#     api_key=os.environ.get("GEMINI_API_KEY", "n/a"),
#     model="gemini-2.5-flash",
#     max_retries=5,
#     request_timeout=120,
# ) 
    # Create task delegation tool
    # Models will be loaded from runtime context in the tool execution
    task_tool = create_task_delegation_tool(
        model=subagent_model,
        researcher_model=subagent_model
    )
    
    # Main agent tools: orchestration + direct write capabilities
    main_agent_tools = TOOLS + [task_tool]
    
    print("🧠 Building Deep Research Agent...")
    print(f"  Main Agent: {len(main_agent_tools)} tools (orchestration + writing)")
    print(f"    - Model: {ctx.model} (configurable via Studio)")
    print(f"    - Direct tools: read_todos, write_todos, think_strategically, write_file, edit_file")
    print("  Sub-agents (for context gathering):")
    print(f"    - internet_researcher: Web search specialist")
    print(f"      Model: {ctx.subagent_model} (configurable via Studio)")
    print(f"    - filesystem_reader: File system reader (read-only)")
    print(f"      Model: {ctx.subagent_model} (configurable via Studio)")
    print(f"    - script_executor: Script execution specialist")
    print(f"      Model: {ctx.subagent_model} (configurable via Studio)")
    print(f"    - biomedical_researcher: RAG knowledge base specialist")
    print(f"      Model: {ctx.subagent_model} (configurable via Studio)")
    
    # Create the main agent using create_react_agent
    # Disable parallel tool calls to prevent concurrent state updates
    graph = create_react_agent(
        main_model.bind(parallel_tool_calls=True),
        tools=main_agent_tools,
        state_schema=DeepAgentState,
        prompt=prompts.SYSTEM_PROMPT
    )

    # Make the graph configurable with a high default recursion limit
    graph = graph.with_config({"recursion_limit": 50000})

    print("✅ Deep Research Agent ready!")
    return graph


# Build the agent graph
# Note: This runs at module import time for LangGraph
# Runtime configuration happens via Runtime[Context] injection
graph = _build_agent_graph()

__all__ = ["graph"]
