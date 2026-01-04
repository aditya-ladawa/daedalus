"""Tools for the Deep Agent including web search, task planning, and execution.

This module provides example tools for web scraping, search functionality, task management,
and safe command execution within a restricted directory.
"""

import os
import subprocess
from pathlib import Path
from typing import Annotated, Any, Callable, List, NotRequired, Optional, cast

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.types import Command
from tavily import TavilyClient
from typing_extensions import TypedDict

from agent_graph.context import Context
from agent_graph.state import DeepAgentState, Todo
from agent_graph import prompts

# Import RAG tool
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from rag.rag_search_tool import search_research_papers

load_dotenv()

# Initialize Tavily client
tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

# Get project root directory for bash tool restrictions
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
ALLOWED_WORK_DIR = PROJECT_ROOT / "agent_workspace"

# Create workspace directory if it doesn't exist
ALLOWED_WORK_DIR.mkdir(exist_ok=True)


@tool(parse_docstring=True)
def web_search(query: str) -> str:
    """Search the web for current information on any topic.

    Args:
        query: The search query to look up.

    Returns:
        Search results with relevant information.
    """
    response = tavily_client.search(query, max_results=5)

    # Format results
    results = []
    for result in response.get("results", []):
        results.append(
            f"**{result['title']}**\n{result['content']}\nURL: {result['url']}\n"
        )

    return "\n---\n".join(results) if results else "No results found."


# Todo tools


@tool
def read_todos(
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """Read the current todo list from the agent state.

    This tool allows the agent to retrieve and review the current todo list
    to stay focused on remaining tasks and track progress through complex workflows.

    Returns:
        Formatted string representation of the current todo list
    """
    todos = state.get("todos", [])
    if not todos:
        return "No todos currently in the list."

    result = "Current TODO List:\n"
    for i, todo in enumerate(todos, 1):
        status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}
        emoji = status_emoji.get(todo["status"], "❓")
        result += f"{i}. {emoji} {todo['content']} ({todo['status']})\n"

    return result.strip()


@tool(parse_docstring=True)
def write_todos(
    todos: list[Todo], tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Create, update, or evolve the agent's todo list based on evidence.

    This process follows a Bayesian plan evolution approach, where the initial plan is
    treated as a "prior" and updated as evidence is gathered. This involves:

    *   Confirm: If findings match expectations, the plan is kept (exploitation).
    *   Evolve: If a stronger signal or angle is found, the plan pivots to explore it (exploration).
    *   Prune: If a direction yields no relevant data, it is removed from the plan.
    *   Deepen: If a topic proves rich, it is broken down further into more granular tasks.

    The plan should be refined based on the quality and content of the findings,
    rather than making changes simply for the sake of it.

    Args:
        todos: List of todo items with content and status

    Returns:
        Command to update agent state with new todo list
    """
    return Command(
        update={
            "todos": todos,
            "messages": [
                ToolMessage(f"Updated todo list to {todos}", tool_call_id=tool_call_id)
            ],
        }
    )


import glob

def validate_path(path_str: str) -> Path:
    """Validate that a path is within the allowed workspace."""
    try:
        # Handle absolute paths that might be inside the workspace
        path = Path(path_str)
        if path.is_absolute():
             # If absolute, check if it starts with ALLOWED_WORK_DIR
             try:
                 path = path.relative_to(ALLOWED_WORK_DIR)
             except ValueError:
                 # If not relative to workspace, try resolving it strictly
                 pass
        
        # Resolve full path (handling .. etc)
        full_path = (ALLOWED_WORK_DIR / path).resolve()
        
        # Check security (must be inside allowed dir)
        # Exception: allow reading project root md2pdf.py
        if full_path == PROJECT_ROOT / "md2pdf.py":
            return full_path
            
        if not str(full_path).startswith(str(ALLOWED_WORK_DIR)):
            raise ValueError(f"Access denied: Path {path_str} is outside workspace")
            
        return full_path
    except Exception as e:
        raise ValueError(f"Invalid path {path_str}: {str(e)}")

@tool(parse_docstring=True)
def list_directory(path: str = ".") -> str:
    """List contents of a directory (ls).

    Args:
        path: Directory path to list (default: current directory)

    Returns:
        List of files and directories
    """
    try:
        target_path = validate_path(path)
        if not target_path.exists():
            return f"Error: Directory {path} does not exist"
        if not target_path.is_dir():
            return f"Error: {path} is not a directory"
            
        items = []
        for item in target_path.iterdir():
            type_symbol = "📁" if item.is_dir() else "📄"
            items.append(f"{type_symbol} {item.name}")
        return "\n".join(sorted(items))
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@tool(parse_docstring=True)
def read_file(path: str) -> str:
    """Read complete contents of a file.

    Args:
        path: Path to the file to read

    Returns:
        Full content of the file
    """
    try:
        target_path = validate_path(path)
        if not target_path.exists():
            return f"Error: File {path} does not exist"
        if not target_path.is_file():
            return f"Error: {path} is not a file"
            
        return target_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool(parse_docstring=True)
def write_file(path: str, content: str) -> str:
    """Create new files or completely overwrite existing ones.

    IMPORTANT: This overwrites the entire file. Use edit_file for partial edits.

    Args:
        path: Path to the file to write
        content: The full content to write to the file

    Returns:
        Success message
    """
    try:
        target_path = validate_path(path)
        # Ensure parent exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@tool(parse_docstring=True)
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Edit specific sections of files without full replacement.

    Replaces the FIRST occurrence of `old_text` with `new_text`.
    Be specific with `old_text` to ensure you match the correct section.

    Args:
        path: Path to the file to edit
        old_text: The exact text segment to replace
        new_text: The new text to insert in its place

    Returns:
        Success message or error if old_text not found
    """
    try:
        target_path = validate_path(path)
        if not target_path.exists():
            return f"Error: File {path} does not exist"
        
        content = target_path.read_text(encoding="utf-8")
        if old_text not in content:
            return f"Error: old_text not found in {path}. Please check exact spelling and whitespace."
            
        # Replace only the first occurrence to be safe
        new_content = content.replace(old_text, new_text, 1)
        target_path.write_text(new_content, encoding="utf-8")
        return f"Successfully updated {path}"
    except Exception as e:
        return f"Error editing file: {str(e)}"

@tool(parse_docstring=True)
def file_search(pattern: str) -> str:
    """Find files matching a pattern (glob).

    Args:
        pattern: Glob pattern (e.g., "*.py", "src/**/*.ts")

    Returns:
        List of matching file paths
    """
    try:
        # Glob is complex to sandbox perfectly with relative paths, 
        # so we list everything in workspace and filter.
        # But efficiently: we chdir to workspace first.
        original_cwd = os.getcwd()
        os.chdir(ALLOWED_WORK_DIR)
        try:
            matches = glob.glob(pattern, recursive=True)
            if not matches:
                return "No files found matching pattern."
            return "\n".join(matches)
        finally:
            os.chdir(original_cwd)
    except Exception as e:
        return f"Error searching files: {str(e)}"

@tool(parse_docstring=True)
def file_content_search(pattern: str, file_pattern: str = "*") -> str:
    """Search file contents for patterns/text (grep).

    Args:
        pattern: Text or regex pattern to search for
        file_pattern: Glob pattern for files to search in (default: *)

    Returns:
        List of matches with line numbers
    """
    try:
        original_cwd = os.getcwd()
        os.chdir(ALLOWED_WORK_DIR)
        try:
            files = glob.glob(file_pattern, recursive=True)
            results = []
            for file_path in files:
                path = Path(file_path)
                if path.is_file():
                    try:
                        lines = path.read_text(encoding="utf-8").splitlines()
                        for i, line in enumerate(lines, 1):
                            if pattern in line:
                                results.append(f"{file_path}:{i}: {line.strip()}")
                    except (UnicodeDecodeError, Exception):
                        pass # Skip binary or unreadable files
            
            if not results:
                return "No matches found."
            return "\n".join(results[:100]) # Limit output
        finally:
            os.chdir(original_cwd)
    except Exception as e:
        return f"Error searching content: {str(e)}"


@tool(parse_docstring=True)
def think_strategically(reflection: str) -> str:
    """Tool for deep strategic thinking, analysis, and planning.

    Use this tool frequently (e.g., after every search or major step) to pause,
    reflect, and ensure research depth and quality.
    
    CRITICAL: Do not just summarize what you did. ANALYZE it.

    Use this tool to:
    1. Analyze Findings: What specifically did I learn? Is the data hard (numbers/facts) or soft (opinions)?
    2. Identify Gaps: What is missing? Do I have specific case studies, quantitative data, methodology details, or contrasting viewpoints?
    3. Assess Quality: Is this satisfied with "overview" level, or is it "deep dive" quality? Would a domain expert find this novel? Are citations authoritative?
    4. Plan Next Steps: If data is shallow -> "Search for X specific dataset". If bias is present -> "Search for counter-arguments". If overview complete -> "Deep dive into sub-topic Y".

    Example Reflection: "I found general salary ranges, but lack specific data on regional variance in Munich vs Berlin. The sources are mostly news articles; I need academic papers or primary government reports to validate these claims. Strategy: Switch focus to 'primary data sources for German AI wages' and look for methodology sections."

    Args:
        reflection: Your deep analysis of the current state, gaps, quality, and specific plan for the next steps.

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"


@tool(parse_docstring=True)
def execute_bash(
    command: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """Execute bash commands in a restricted agent workspace directory.

    IMPORTANT: This tool is restricted to the agent_workspace directory for security.
    All commands will be executed in the agent_workspace subdirectory.

    Security & Environment rules:
    - Environment: ALWAYS use the existing `.venv`. Do NOT create new venvs.
    - Languages: Execute ONLY Python scripts or simple bash commands (cat, grep, etc). No Node/JS.
    - Installation: Do NOT define new requirements.txt or install packages unless critical. Use what's available.
    - Restrictions: Cannot access files outside agent_workspace (except project root for .venv/md2pdf.py), Cannot modify system files

    Common use cases:
    - Run Python scripts: `source ../.venv/bin/activate && python script.py`
    - Create/Edit files: `echo "..." > file.md`, `sed -i ...`
    - Generate PDF: `source ../.venv/bin/activate && python ../md2pdf.py input.md output.pdf`
    - Data processing: pandas, numpy scripts (in .venv)

    Args:
        command: The bash command to execute

    Returns:
        Command output or error message
    """

    try:
        # Change to workspace directory
        original_dir = os.getcwd()
        os.chdir(ALLOWED_WORK_DIR)

        # Activate virtual environment if it exists
        venv_activate = PROJECT_ROOT / ".venv" / "bin" / "activate"
        if venv_activate.exists():
            # Prepend activation command
            command = f"source {venv_activate} && {command}"

        # Execute command with shell (use bash explicitly to support 'source')
        result = subprocess.run(
            command,
            shell=True,
            executable='/bin/bash',  # Use bash instead of /bin/sh to support 'source'
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=str(ALLOWED_WORK_DIR),
        )

        # Change back to original directory
        os.chdir(original_dir)

        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"

        if result.returncode != 0:
            output = f"Command failed with exit code {result.returncode}\n{output}"

        return output if output else "Command executed successfully (no output)"

    except subprocess.TimeoutExpired:
        os.chdir(original_dir)
        return "Error: Command timed out after 5 minutes"
    except Exception as e:
        os.chdir(original_dir)
        return f"Error executing command: {str(e)}"


# Task delegation infrastructure


class SubAgent(TypedDict):
    """Configuration for a specialized sub-agent."""

    name: str
    description: str
    prompt: str
    tools: NotRequired[list[str]]


def _create_task_tool(tools, subagents: list[SubAgent], model, state_schema, researcher_model=None):
    """Create a task delegation tool that enables context isolation through sub-agents.

    This function implements the core pattern for spawning specialized sub-agents with
    isolated contexts, preventing context clash and confusion in complex multi-step tasks.

    Args:
        tools: List of available tools that can be assigned to sub-agents
        subagents: List of specialized sub-agent configurations
        model: The language model to use for main/default agents
        state_schema: The state schema (typically DeepAgentState)
        researcher_model: Optional separate model for researcher agent
        coding_model: Optional separate model for coding/coder agent

    Returns:
        A 'task' tool that can delegate work to specialized sub-agents
    """
    # Create agent registry
    agents = {}

    # Build tool name mapping for selective tool assignment
    tools_by_name = {}
    for tool_ in tools:
        if not isinstance(tool_, BaseTool):
            tool_ = tool(tool_)
        tools_by_name[tool_.name] = tool_

    # Create specialized sub-agents based on configurations
    for _agent in subagents:
        if "tools" in _agent:
            # Use specific tools if specified
            _tools = [tools_by_name[t] for t in _agent["tools"]]
        else:
            # Default to all tools
            _tools = tools

        # Select appropriate model based on agent type
        if _agent["name"] == "internet_researcher" and researcher_model:
            agent_model = researcher_model
        else:
            agent_model = model

        agents[_agent["name"]] = create_react_agent(
            agent_model,
            prompt=_agent["prompt"],
            tools=_tools,
            state_schema=state_schema,
        )

    # Generate description of available sub-agents for the tool description
    other_agents_string = [
        f"- {_agent['name']}: {_agent['description']}" for _agent in subagents
    ]

    @tool(description=prompts.TASK_DESCRIPTION_PREFIX.format(other_agents=other_agents_string))
    async def task(
        description: str,
        subagent_type: str,
        state: Annotated[state_schema, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        """Delegate a task to a specialized sub-agent with isolated context.

        This creates a fresh context for the sub-agent containing only the task description,
        preventing context pollution from the parent agent's conversation history.
        """
        # Validate requested agent type exists
        if subagent_type not in agents:
            return f"Error: invoked agent of type {subagent_type}, the only allowed types are {[f'`{k}`' for k in agents]}"

        # Get the requested sub-agent
        sub_agent = agents[subagent_type]

        # Create isolated context with only the task description
        # This is the key to context isolation - no parent history
        state["messages"] = [{"role": "user", "content": description}]

        # Execute the sub-agent in isolation (async)
        result = await sub_agent.ainvoke(state, config={"recursion_limit": 20000})

        # Return results to parent agent via Command state update
        return Command(
            update={
                "files": result.get("files", {}),  # Merge any file changes
                "messages": [
                    # Sub-agent result becomes a ToolMessage in parent context
                    ToolMessage(
                        result["messages"][-1].content, tool_call_id=tool_call_id
                    )
                ],
            }
        )

    return task


# ============================================================================
# SUB-AGENT CONFIGURATIONS
# ============================================================================

# Define specialized sub-agent configurations for the research agent
SUB_AGENTS: List[SubAgent] = [
    SubAgent(
        name="internet_researcher",
        description="Web research specialist - conducts comprehensive, multi-angle research and returns FULL findings without summarization",
        prompt=prompts.INTERNET_RESEARCHER_PROMPT,
        tools=["web_search", "think_strategically"],
    ),
    SubAgent(
        name="file_manager",
        description="File operations specialist - reads, writes, updates, and manages .md research files using bash commands",
        prompt=prompts.FILE_MANAGER_PROMPT,
        tools=["list_directory", "read_file", "write_file", "edit_file", "file_search", "file_content_search", "execute_bash"],
    ),
    SubAgent(
        name="biomedical_researcher",
        description="Biomedical research specialist - queries knowledge base of sleep disorders, psychiatric conditions, and Mendelian randomization studies",
        prompt=prompts.BIOMEDICAL_RESEARCHER_PROMPT,
        tools=["search_research_papers"],
    ),
]


def create_task_delegation_tool(
    model, 
    researcher_model=None,
    subagents=None,
    tools=None,
):
    """Create the task delegation tool with configured sub-agents.

    This is the public API for creating a task delegation tool for the research agent.
    
    Args:
        model: The language model to use for sub-agents (default/fallback)
        researcher_model: Optional separate model for internet_researcher agent
        subagents: Optional list of SubAgent configurations. If not provided, uses SUB_AGENTS
        tools: Optional list of tools available to sub-agents. If not provided, uses ALL_TOOLS

    Returns:
        The task delegation tool configured with the specified sub-agents
        
    Example:
        # Use default sub-agents (internet_researcher, file_manager)
        task_tool = create_task_delegation_tool(model)
        
        # Use custom sub-agents with different models
        custom_agents = [
            {
                "name": "researcher",
                "description": "Research specialist",
                "prompt": RESEARCHER_PROMPT,
                "tools": ["web_search", "think_strategically"]
            }
        ]
        task_tool = create_task_delegation_tool(
            model=main_llm,
            researcher_model=researcher_llm,
            subagents=custom_agents,
            tools=all_tools
        )
    """
    return _create_task_tool(
        tools=tools if tools is not None else ALL_TOOLS,
        subagents=subagents if subagents is not None else SUB_AGENTS,
        model=model,
        state_schema=DeepAgentState,
        researcher_model=researcher_model,
    )


# ============================================================================
# TOOL ORGANIZATION FOR DEEP RESEARCH AGENT
#
# Architecture for Long-Running Research Agent:
# - Main Agent: Orchestrator (strategic planning, task delegation ONLY)
# - Sub-Agent 1: Internet Researcher (web search specialist)
# - Sub-Agent 2: File Manager (file operations via bash for .md research files)
#
# Design Philosophy:
# - Main agent focuses on high-level strategy and delegation
# - Sub-agents are specialists that do the actual work
# - This prevents context pollution and maintains focus
#
# ============================================================================

# Main Agent Tools (Orchestration ONLY)
# The main agent ONLY plans and delegates - it doesn't do the work itself
MAIN_AGENT_TOOLS: List[Callable[..., Any]] = [
    read_todos,
    write_todos,
    think_strategically,
    # task tool will be added dynamically when created
]

# Internet Researcher Sub-Agent Tools
# Specialized for web research and information gathering
RESEARCHER_TOOLS: List[Callable[..., Any]] = [
    web_search,
    think_strategically,  # Researcher can also reflect on findings
]

# File Manager Sub-Agent Tools
# Specialized for ALL file operations using localized Python tools + bash
# This sub-agent handles: read, write, append, update, search in .md files
FILE_MANAGER_TOOLS: List[Callable[..., Any]] = [
    list_directory,
    read_file,
    write_file,
    edit_file,
    file_search,
    file_content_search,
    execute_bash,
]

# All available tools (for reference and sub-agent creation)
ALL_TOOLS: List[Callable[..., Any]] = [
    web_search,
    read_todos,
    write_todos,
    think_strategically,
    list_directory,
    read_file,
    write_file,
    edit_file,
    file_search,
    file_content_search,
    execute_bash,
    search_research_papers,
]

# Default TOOLS for main agent (just orchestration)
# The 'task' delegation tool will be added to this list dynamically
TOOLS: List[Callable[..., Any]] = MAIN_AGENT_TOOLS
