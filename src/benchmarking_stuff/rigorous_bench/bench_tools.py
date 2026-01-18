"""Tools for RigorousBench Deep Research Agent.

Provides restricted bash execution (all_reports/ only), report writing,
and task delegation to specialized subagents.
"""

import os
import subprocess
from pathlib import Path
from typing import Annotated, List, NotRequired

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.types import Command
from typing_extensions import TypedDict

# Import state from agent_graph
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agent_graph"))
from state import DeepAgentState, Todo

# Import prompts
import bench_prompts

load_dotenv()

# =============================================================================
# PATH CONFIGURATION - RESTRICTED TO all_reports/
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
BENCH_DIR = Path(__file__).parent.absolute()
REPORTS_DIR = BENCH_DIR / "all_reports"

# Ensure reports directory exists
REPORTS_DIR.mkdir(exist_ok=True)


def validate_reports_path(path_str: str, must_exist: bool = False) -> Path:
    """Validate path is within all_reports/ directory.
    
    Args:
        path_str: Path string to validate
        must_exist: If True, path must already exist
        
    Returns:
        Validated absolute path
        
    Raises:
        ValueError: If path is outside all_reports/
    """
    path = Path(path_str)
    
    # Make absolute if relative
    if not path.is_absolute():
        full_path = (REPORTS_DIR / path).resolve()
    else:
        full_path = path.resolve()
    
    # Must be inside REPORTS_DIR
    try:
        full_path.relative_to(REPORTS_DIR)
    except ValueError:
        raise ValueError(
            f"Access denied: Path {path_str} is outside all_reports/. "
            f"All operations are restricted to: {REPORTS_DIR}"
        )
    
    if must_exist and not full_path.exists():
        raise ValueError(f"Path does not exist: {path_str}")
    
    return full_path


# =============================================================================
# REPORT WRITING TOOL
# =============================================================================

@tool(parse_docstring=True)
def write_report(query_id: str, content: str, filename: str = "report.md") -> str:
    """Write a research report to all_reports/{query_id}/{filename}.
    
    Creates the query directory if it doesn't exist.
    
    Args:
        query_id: Unique identifier for the query (e.g., "07001")
        content: Full markdown content of the report
        filename: Name of the file (default: report.md)
    
    Returns:
        Success message with file path
    """
    try:
        # Create query directory
        query_dir = REPORTS_DIR / query_id
        query_dir.mkdir(parents=True, exist_ok=True)
        
        # Write report
        report_path = query_dir / filename
        report_path.write_text(content, encoding="utf-8")
        
        return f"Successfully wrote {len(content)} characters to {report_path.relative_to(BENCH_DIR)}"
    except Exception as e:
        return f"Error writing report: {str(e)}"


@tool(parse_docstring=True)
def read_report_lines(query_id: str, start_line: int = 1, end_line: int = 50, filename: str = "report.md") -> str:
    """Read specific lines from a report file.
    
    Use to review sections of the report without loading the entire file.
    
    Args:
        query_id: Query ID of the report
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (inclusive)
        filename: Name of the file (default: report.md)
    
    Returns:
        Lines from the file with line numbers
    """
    try:
        report_path = REPORTS_DIR / query_id / filename
        if not report_path.exists():
            return f"Error: Report not found at {query_id}/{filename}"
        
        lines = report_path.read_text(encoding="utf-8").splitlines()
        total_lines = len(lines)
        
        # Clamp to valid range
        start_line = max(1, start_line)
        end_line = min(total_lines, end_line)
        
        result = f"Lines {start_line}-{end_line} of {total_lines}:\n"
        for i in range(start_line - 1, end_line):
            result += f"{i+1:4d}: {lines[i]}\n"
        
        return result
    except Exception as e:
        return f"Error reading report: {str(e)}"


@tool(parse_docstring=True)
def grep_report(query_id: str, pattern: str, filename: str = "report.md") -> str:
    """Search for a pattern in a report file.
    
    Returns matching lines with line numbers for targeted reading or editing.
    
    Args:
        query_id: Query ID of the report
        pattern: Text pattern to search for (case-insensitive)
        filename: Name of the file (default: report.md)
    
    Returns:
        Matching lines with line numbers
    """
    try:
        report_path = REPORTS_DIR / query_id / filename
        if not report_path.exists():
            return f"Error: Report not found at {query_id}/{filename}"
        
        lines = report_path.read_text(encoding="utf-8").splitlines()
        matches = []
        
        pattern_lower = pattern.lower()
        for i, line in enumerate(lines, 1):
            if pattern_lower in line.lower():
                matches.append(f"{i:4d}: {line}")
        
        if not matches:
            return f"No matches found for '{pattern}'"
        
        return f"Found {len(matches)} matches:\n" + "\n".join(matches)
    except Exception as e:
        return f"Error searching report: {str(e)}"


@tool(parse_docstring=True)  
def edit_report(query_id: str, old_text: str, new_text: str, filename: str = "report.md") -> str:
    """Edit a specific section of a report by replacing text.
    
    Replaces the FIRST occurrence of old_text with new_text.
    Use grep_report first to find the exact text to replace.
    
    Args:
        query_id: Query ID of the report
        old_text: Exact text to find and replace
        new_text: New text to insert
        filename: Name of the file (default: report.md)
    
    Returns:
        Success message or error
    """
    try:
        report_path = REPORTS_DIR / query_id / filename
        if not report_path.exists():
            return f"Error: Report not found at {query_id}/{filename}"
        
        content = report_path.read_text(encoding="utf-8")
        
        if old_text not in content:
            return f"Error: old_text not found in report. Use grep_report to find exact text."
        
        new_content = content.replace(old_text, new_text, 1)
        report_path.write_text(new_content, encoding="utf-8")
        
        return f"Successfully updated {query_id}/{filename}"
    except Exception as e:
        return f"Error editing report: {str(e)}"


@tool(parse_docstring=True)
def read_file(path: str) -> str:
    """Read a file from all_reports/ directory.
    
    Args:
        path: Path relative to all_reports/
    
    Returns:
        File contents
    """
    try:
        full_path = validate_reports_path(path, must_exist=True)
        return full_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool(parse_docstring=True)
def list_directory(path: str = ".") -> str:
    """List contents of a directory within all_reports/.
    
    Args:
        path: Directory path relative to all_reports/
    
    Returns:
        List of files and directories
    """
    try:
        full_path = validate_reports_path(path, must_exist=True)
        if not full_path.is_dir():
            return f"Error: {path} is not a directory"
        
        items = []
        for item in sorted(full_path.iterdir()):
            symbol = "📁" if item.is_dir() else "📄"
            items.append(f"{symbol} {item.name}")
        
        return "\n".join(items) if items else "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


# =============================================================================
# RESTRICTED BASH EXECUTOR
# =============================================================================

@tool(parse_docstring=True)
def execute_bash_restricted(
    command: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """Execute bash commands RESTRICTED to all_reports/ directory only.
    
    The virtual environment (.venv) is automatically activated.
    Working directory is set to all_reports/.
    
    Security restrictions:
    - Can ONLY access files within all_reports/
    - Cannot install packages
    - Cannot make network requests
    - Cannot modify system files
    
    Args:
        command: Bash command to execute
    
    Returns:
        Command output or error
    """
    try:
        original_dir = os.getcwd()
        os.chdir(REPORTS_DIR)
        
        # Activate virtual environment
        venv_activate = PROJECT_ROOT / ".venv" / "bin" / "activate"
        if venv_activate.exists():
            command = f"source {venv_activate} && {command}"
        
        result = subprocess.run(
            command,
            shell=True,
            executable='/bin/bash',
            capture_output=True,
            text=True,
            timeout=60,  # 1 minute timeout
            cwd=str(REPORTS_DIR),
        )
        
        os.chdir(original_dir)
        
        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"
        
        if result.returncode != 0:
            output = f"Command failed (exit {result.returncode})\n{output}"
        
        return output if output.strip() else "Command executed (no output)"
        
    except subprocess.TimeoutExpired:
        os.chdir(original_dir)
        return "Error: Command timed out after 60 seconds"
    except Exception as e:
        os.chdir(original_dir)
        return f"Error: {str(e)}"


# =============================================================================
# TODO MANAGEMENT TOOLS
# =============================================================================

@tool
def read_todos(
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """Read the current todo list from agent state.
    
    Returns:
        Formatted todo list
    """
    todos = state.get("todos", [])
    if not todos:
        return "No todos in the list."
    
    result = "Current TODOs:\n"
    for i, todo in enumerate(todos, 1):
        emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(
            todo["status"], "❓"
        )
        result += f"{i}. {emoji} {todo['content']} ({todo['status']})\n"
    
    return result.strip()


@tool(parse_docstring=True)
def write_todos(
    todos: list[Todo],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Update the todo list for tracking research progress.
    
    Args:
        todos: List of todo items with content and status
    
    Returns:
        Command to update state
    """
    return Command(
        update={
            "todos": todos,
            "messages": [
                ToolMessage(f"Updated todos: {len(todos)} items", tool_call_id=tool_call_id)
            ],
        }
    )


# =============================================================================
# STRATEGIC THINKING TOOL
# =============================================================================

@tool(parse_docstring=True)
def think_strategically(reflection: str) -> str:
    """Pause for strategic thinking and planning.
    
    Use to analyze findings, identify gaps, and plan next steps.
    
    Args:
        reflection: Your analysis of current state and next steps
    
    Returns:
        Confirmation
    """
    return f"Strategic reflection recorded: {reflection}"


# =============================================================================
# MCP TOOLS LOADER (Tavily MCP)
# =============================================================================

from internet_search_mcp import get_mcp_tools


async def load_mcp_research_tools():
    """Load Tavily MCP tools asynchronously.
    
    Returns:
        List of LangChain-compatible MCP tools
    """
    return await get_mcp_tools()


# =============================================================================
# TOOL COLLECTIONS
# =============================================================================

# Main agent tools (orchestration + report writing + reading + file ops)
MAIN_AGENT_TOOLS = [
    write_report,
    read_report_lines,
    grep_report,
    edit_report,
    read_file,      # General file reading in all_reports/
    list_directory, # List directories
    read_todos,
    write_todos,
    think_strategically,
]

# Script executor subagent tools (filesystem ops + section reading)
EXECUTOR_TOOLS = [
    execute_bash_restricted,
    list_directory,
    read_file,
    read_report_lines,
    grep_report,
]

# Note: RESEARCHER_TOOLS are loaded dynamically from MCP via load_mcp_research_tools()


# =============================================================================
# SUBAGENT CONFIGURATIONS
# =============================================================================

class SubAgent(TypedDict):
    """Configuration for a specialized sub-agent."""
    name: str
    description: str
    prompt: str
    tools: NotRequired[list[str]]


SUB_AGENTS: List[SubAgent] = [
    SubAgent(
        name="internet_researcher",
        description="Web research specialist using Tavily - gathers comprehensive sources with URLs for citation",
        prompt=bench_prompts.INTERNET_RESEARCHER_PROMPT,
        tools=["web_search", "think_strategically"],
    ),
    SubAgent(
        name="script_executor",
        description="Script execution restricted to all_reports/ directory - for file operations, data processing, and reading/searching report sections",
        prompt=bench_prompts.SCRIPT_EXECUTOR_PROMPT,
        tools=["execute_bash_restricted", "list_directory", "read_file", "read_report_lines", "grep_report"],
    ),
]


# =============================================================================
# TASK DELEGATION TOOL
# =============================================================================

async def create_task_tool_async(model, state_schema):
    """Create task delegation tool with MCP tools loaded asynchronously."""
    
    # Load MCP tools for internet researcher
    mcp_tools = await load_mcp_research_tools()
    
    # Combine with think_strategically for researcher
    researcher_tools = mcp_tools + [think_strategically]
    
    # Create script executor tools
    executor_tools = EXECUTOR_TOOLS
    
    # Build subagents
    agents = {
        "internet_researcher": create_react_agent(
            model.bind(parallel_tool_calls=False),
            prompt=bench_prompts.INTERNET_RESEARCHER_PROMPT,
            tools=researcher_tools,
            state_schema=state_schema,
        ),
        "script_executor": create_react_agent(
            model.bind(parallel_tool_calls=False),
            prompt=bench_prompts.SCRIPT_EXECUTOR_PROMPT,
            tools=executor_tools,
            state_schema=state_schema,
        ),
    }
    
    agents_description = [
        "- internet_researcher: Web research specialist using Tavily MCP - gathers comprehensive sources with URLs",
        "- script_executor: Script execution restricted to all_reports/ directory - handles file operations and reading/searching report sections",
    ]
    
    @tool(description=bench_prompts.TASK_DESCRIPTION_PREFIX.format(other_agents=agents_description))
    async def task(
        description: str,
        subagent_type: str,
        state: Annotated[state_schema, InjectedState],
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
            state["messages"] = [{"role": "user", "content": description}]
            
            result = await sub_agent.ainvoke(state, config={"recursion_limit": 50})
            
            if not result.get("messages"):
                raise ValueError("Subagent returned no messages")
            
            final_msg = result["messages"][-1]
            content = getattr(final_msg, "content", str(final_msg))
            
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
    
    return task


async def create_task_delegation_tool_async(model):
    """Create task delegation tool with MCP tools loaded asynchronously.
    
    Args:
        model: LLM to use for subagents
    
    Returns:
        Task delegation tool (must be awaited)
    """
    return await create_task_tool_async(
        model=model,
        state_schema=DeepAgentState,
    )
