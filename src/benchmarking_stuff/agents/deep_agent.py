"""RigorousBench Deep Research Agent using LangGraph.

Architecture (mirrors src/agent_graph/):
- Main Agent: DeepSeek (orchestration + report writing section by section)
- Subagents: Gemini 2.5 Flash
- Tools: Shared tools from agents/tools.py + custom delegation
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Annotated, Literal, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage, AnyMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.graph import add_messages
from langgraph.types import Command
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from typing_extensions import NotRequired

# Import shared config
try:
    from .config import (
        DEEP_AGENT_MODEL,
        DEEP_AGENT_PROVIDER,
        DEEP_AGENT_BASE_URL,
        DEEP_AGENT_TEMPERATURE,
        SUBAGENT_MODEL,
        SUBAGENT_TEMPERATURE,
        DEEPSEEK_API_KEY,
        GEMINI_API_KEY,
    )
    from .tools import (
        create_report_tools,
        create_bash_tool,
        web_search,
        think_strategically,
        read_todos,
        write_todos
    )
    from .prompts_deep_agent import (
        SYSTEM_PROMPT, 
        INITIAL_USER_MESSAGE,
        INTERNET_RESEARCHER_PROMPT,
        SCRIPT_EXECUTOR_PROMPT,
        TASK_DESCRIPTION_PREFIX
    )
except ImportError:
    # Fallback for running as script
    sys.path.append(str(Path(__file__).parent))
    from config import (
        DEEP_AGENT_MODEL,
        DEEP_AGENT_PROVIDER,
        DEEP_AGENT_BASE_URL,
        DEEP_AGENT_TEMPERATURE,
        SUBAGENT_MODEL,
        DEEPSEEK_API_KEY,
        GEMINI_API_KEY,
    )
    from tools import (
        create_report_tools,
        create_bash_tool,
        web_search,
        think_strategically,
        read_todos,
        write_todos
    )
    from prompts_deep_agent import (
        SYSTEM_PROMPT, 
        INITIAL_USER_MESSAGE,
        INTERNET_RESEARCHER_PROMPT,
        SCRIPT_EXECUTOR_PROMPT,
        TASK_DESCRIPTION_PREFIX
    )

load_dotenv()

# Constants
AGENTS_DIR = Path(__file__).parent
EVAL_REPORTS_DIR = AGENTS_DIR.parent / "eval_reports"
REPORTS_DIR = EVAL_REPORTS_DIR / "rigorous_bench" / "deep_agent"
PROJECT_ROOT = AGENTS_DIR.parent.parent.parent


# =============================================================================
# STATE DEFINITION
# =============================================================================

class Todo(TypedDict):
    """A structured task item for tracking progress through complex workflows.

    Attributes:
        content: Short, specific description of the task
        status: Current state - pending, in_progress, or completed
    """
    content: str
    status: Literal["pending", "in_progress", "completed"]


class DeepAgentState(AgentState):
    """Agent state with scratchpad (todos) for complex workflow tracking.

    Extends AgentState which provides:
    - messages: List of conversation messages
    - remaining_steps: Managed field for recursion control

    Adds:
    - todos: Optional task tracking for complex workflows
    """
    todos: NotRequired[list[Todo]]


# =============================================================================
# TASK DELEGATION
# =============================================================================

async def create_task_delegation_tool_async(model):
    """Create task delegation tool with subagents."""
    
    # Initialize tools
    report_tools = create_report_tools(REPORTS_DIR)
    bash_tool = create_bash_tool(REPORTS_DIR, PROJECT_ROOT)
    
    # Define subagent tools
    researcher_tools = [web_search, think_strategically]
    
    # Executor gets bash + report reading/searching tools
    executor_tools = [bash_tool] + report_tools
    
    # Build subagents map
    agents = {
        "internet_researcher": create_react_agent(
            model.bind(parallel_tool_calls=False),
            prompt=INTERNET_RESEARCHER_PROMPT,
            tools=researcher_tools,
            state_schema=DeepAgentState,
        ),
        "script_executor": create_react_agent(
            model.bind(parallel_tool_calls=False),
            prompt=SCRIPT_EXECUTOR_PROMPT,
            tools=executor_tools,
            state_schema=DeepAgentState,
        ),
    }
    
    agents_description = [
        "- internet_researcher: Web research specialist - gathers comprehensive sources with URLs",
        "- script_executor: Script execution restricted to reports directory - handles file operations",
    ]
    
    @tool(description=TASK_DESCRIPTION_PREFIX.format(other_agents="\n".join(agents_description)))
    async def task(
        description: str,
        subagent_type: str,
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        """Delegate task to specialized subagent."""
        if subagent_type not in agents:
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            f"Error: Unknown agent '{subagent_type}'. Available: {list(agents.keys())}",
                            tool_call_id=tool_call_id,
                        )
                    ]
                }
            )
        
        try:
            sub_agent = agents[subagent_type]
            # Create a localized state prompt
            sub_state = {"messages": [{"role": "user", "content": description}]}
            
            # Run subagent
            result = await sub_agent.ainvoke(sub_state, config={"recursion_limit": 50})
            
            if not result.get("messages"):
                raise ValueError("Subagent returned no messages")
            
            # Extract final response
            final_msg = result["messages"][-1]
            content = getattr(final_msg, "content", str(final_msg))
            
            # Ensure content is string
            if not isinstance(content, str):
                import json
                try:
                    content = json.dumps(content, indent=2)
                except:
                    content = str(content)
            
            return Command(
                update={"messages": [ToolMessage(content, tool_call_id=tool_call_id)]}
            )
            
        except Exception as e:
            import traceback
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            f"Error in {subagent_type}: {str(e)}\n{traceback.format_exc()}",
                            tool_call_id=tool_call_id,
                        )
                    ]
                }
            )
    
    return task, report_tools


# =============================================================================
# MAIN AGENT
# =============================================================================

async def build_agent_graph(
    main_model_name: str = DEEP_AGENT_MODEL,
    subagent_model_name: str = SUBAGENT_MODEL,
):
    """Build the deep research agent graph."""
    print(f"🧠 Building RigorousBench Agent...")
    print(f"   Main Agent: {main_model_name}")
    print(f"   Subagents: {subagent_model_name}")

    # Main agent: Choose provider based on config
    if DEEP_AGENT_PROVIDER == "google_genai":
        main_model = ChatGoogleGenerativeAI(
            model=main_model_name,
            google_api_key=GEMINI_API_KEY,
            temperature=DEEP_AGENT_TEMPERATURE,
            max_tokens=8192,
        )
    else:  # OpenAI-compatible (DeepSeek, etc.)
        main_model = ChatOpenAI(
            model=main_model_name,
            base_url=DEEP_AGENT_BASE_URL,
            api_key=DEEPSEEK_API_KEY,
            temperature=DEEP_AGENT_TEMPERATURE,
            max_tokens=8192,
        )
    
    # Subagent model: Google Gemini
    subagent_model = ChatGoogleGenerativeAI(
        model=subagent_model_name,
        google_api_key=GEMINI_API_KEY,
        temperature=SUBAGENT_TEMPERATURE,  # Use config value (0.0 for deterministic)
        max_tokens=8192,
    )
    
    # Create task delegation tool
    print("🔧 Loading tools and subagents...")
    task_tool, report_tools = await create_task_delegation_tool_async(model=subagent_model)
    
    # Combine main tools
    all_tools = [task_tool] + report_tools + [read_todos, write_todos, think_strategically]
    
    # Build main agent
    graph = create_react_agent(
        main_model.bind(parallel_tool_calls=True),  # Enable parallel subagent spawning
        tools=all_tools,
        state_schema=DeepAgentState,
        prompt=SYSTEM_PROMPT,
    )
    
    # High recursion limit
    graph = graph.with_config({"recursion_limit": 1000})
    
    return graph


async def run_query(
    query: str,
    query_id: str,
    main_model: str = DEEP_AGENT_MODEL,
    subagent_model: str = SUBAGENT_MODEL,
):
    """Run a research query and generate report."""
    try:
        graph = await build_agent_graph(main_model, subagent_model)
        
        # Ensure report directory exists
        (REPORTS_DIR / query_id).mkdir(parents=True, exist_ok=True)
        
        initial_message = INITIAL_USER_MESSAGE.format(query_id=query_id, query=query)
        
        print(f"\n📝 Processing query {query_id}...")
        
        # Suppress verbose logging
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("langchain").setLevel(logging.WARNING)
        
        print(f"\n{'='*60}")
        print(f"🤖 Agent Stream Output")
        print(f"{'='*60}")
        
        final_messages = []
        async for event in graph.astream(
            {"messages": [{"role": "user", "content": initial_message}]},
            config={"recursion_limit": 1000},
        ):
            for value in event.values():
                if isinstance(value, dict) and "messages" in value:
                    for msg in value["messages"]:
                        # Simple logging
                        type_str = msg.type.upper() if hasattr(msg, "type") else "MSG"
                        content_preview = str(msg.content)[:200]
                        if len(str(msg.content)) > 200: 
                            content_preview += "..."
                        print(f"\n[{type_str}] {content_preview}")
                        final_messages.append(msg)
            
            if "__end__" in event:
                final_messages = event["__end__"]["messages"]
        
        print(f"{'='*60}\n")
        
        if not final_messages:
            return "Error: No response from agent"
        
        content = ""
        for msg in reversed(final_messages):
            if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
                content = msg.content
                break
        
        print(f"✅ Query {query_id} completed")
        return content if content else "Agent completed but no text content found"
        
    except Exception as e:
        import traceback
        error = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Query {query_id} failed: {e}")
        return error


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run RigorousBench deep research agent")
    parser.add_argument("--query", type=str, help="Research query")
    parser.add_argument("--query-id", type=str, default="test", help="Query ID for output")
    parser.add_argument("--main-model", type=str, default=DEEP_AGENT_MODEL, help="Main agent model")
    parser.add_argument("--subagent-model", type=str, default=SUBAGENT_MODEL, help="Subagent model")
    
    args = parser.parse_args()
    
    if args.query:
        asyncio.run(run_query(args.query, args.query_id, args.main_model, args.subagent_model))
    else:
        print("Please provide a --query argument.")
