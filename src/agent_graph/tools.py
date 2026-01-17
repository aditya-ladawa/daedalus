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

# Import DeepEval tracing (no-op if not enabled)
from agent_graph.tracing import observe, update_span

load_dotenv()

# Initialize Tavily client
tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

# Get project root directory for bash tool restrictions
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
ALLOWED_WORK_DIR = PROJECT_ROOT / "agent_workspace"

# Create workspace directory if it doesn't exist
ALLOWED_WORK_DIR.mkdir(exist_ok=True)


@tool(parse_docstring=True)
@observe(type="tool", name="web_search")
def web_search(query: str) -> str:
    """Search the web for current information on any topic.

    This tool uses Tavily AI search optimized for research. It returns comprehensive
    results including titles, content snippets, URLs, and relevance scores.

    Args:
        query: The search query to look up.

    Returns:
        Search results with detailed information and source URLs for citation.
    """
    # Tavily search with basic mode to reduce API costs
    response = tavily_client.search(
        query,
        max_results=5,  # Reduced for cost savings
        search_depth="basic",  # Use basic mode to reduce API consumption
        include_answer=False,  # We want raw results, not LLM-generated answers
        include_raw_content=False,  # Don't need full HTML (too verbose)
        include_domains=[],  # Allow all domains
        exclude_domains=[]  # No exclusions
    )

    # Format results with enhanced information
    results = []
    source_urls = []

    for idx, result in enumerate(response.get("results", []), 1):
        title = result.get('title', 'No title')
        url = result.get('url', '')
        content = result.get('content', 'No content available')
        score = result.get('score', 0)

        # Track URLs for references section
        source_urls.append(f"- [{title}]({url})")

        # Format individual result
        result_text = f"**Result {idx}: {title}**\n"
        result_text += f"Relevance Score: {score:.3f}\n"
        result_text += f"{content}\n"
        result_text += f"Source: {url}\n"

        results.append(result_text)

    if not results:
        return "No results found."

    # Combine results with a references section
    output = "\n---\n".join(results)
    output += "\n\n" + "="*60 + "\n"
    output += "**🔗 REFERENCES (Include these in your final output):**\n"
    output += "\n".join(source_urls)
    output += "\n" + "="*60 + "\n"

    return output


# Todo tools


@tool
@observe(type="tool", name="read_todos")
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
@observe(type="tool", name="write_todos")
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

def validate_path(path_str: str, write_mode: bool = False) -> Path:
    """Validate that a path is accessible.

    Args:
        path_str: Path to validate
        write_mode: If True, restricts to agent_workspace only. If False, allows read access to specific allowed directories.

    Returns:
        Validated absolute path

    Allowed directories:
        Read: agent_workspace/, src/rag/research_paper_results_reports/, src/rag/files_to_embed/, src/scripts_for_agent/
        Write: agent_workspace/ (only)
    """
    try:
        # Handle absolute paths
        path = Path(path_str)
        if path.is_absolute():
            # If absolute, try to make it relative to workspace
            try:
                path = path.relative_to(ALLOWED_WORK_DIR)
            except ValueError:
                # Not in workspace, will be resolved from ALLOWED_WORK_DIR
                pass

        # Resolve full path (handling .. etc)
        full_path = (ALLOWED_WORK_DIR / path).resolve()

        # Security check: Must be inside PROJECT_ROOT (no escaping to parent directories)
        try:
            full_path.relative_to(PROJECT_ROOT)
        except ValueError:
            raise ValueError(f"Access denied: Path {path_str} is outside project root")

        # Write operations: Restricted to agent_workspace only
        if write_mode:
            if not str(full_path).startswith(str(ALLOWED_WORK_DIR)):
                raise ValueError(f"Write access denied: Can only write to agent_workspace/. Path: {path_str}")
            return full_path

        # Read operations: Whitelist specific directories only
        allowed_read_dirs = [
            ALLOWED_WORK_DIR,  # agent_workspace/
            PROJECT_ROOT / "src" / "rag" / "research_paper_results_reports",
            PROJECT_ROOT / "src" / "rag" / "files_to_embed",
            PROJECT_ROOT / "src" / "scripts_for_agent",
        ]

        # Check if path is within any allowed directory
        for allowed_dir in allowed_read_dirs:
            if str(full_path).startswith(str(allowed_dir)):
                return full_path

        # Path is not in any allowed directory
        raise ValueError(
            f"Access denied: Path {path_str} is not in allowed directories. "
            f"Allowed: agent_workspace/, src/rag/research_paper_results_reports/, "
            f"src/rag/files_to_embed/, src/scripts_for_agent/"
        )

    except Exception as e:
        raise ValueError(f"Invalid path {path_str}: {str(e)}")

@tool(parse_docstring=True)
@observe(type="tool", name="list_directory")
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
@observe(type="tool", name="read_file")
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
@observe(type="tool", name="write_file")
def write_file(path: str, content: str) -> str:
    """Create new files or completely overwrite existing ones.

    IMPORTANT: This overwrites the entire file. Use edit_file for partial edits.
    Write access is restricted to agent_workspace/ only for safety.

    Args:
        path: Path to the file to write (must be in agent_workspace/)
        content: The full content to write to the file

    Returns:
        Success message
    """
    try:
        target_path = validate_path(path, write_mode=True)  # Enforce write restrictions
        # Ensure parent exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@tool(parse_docstring=True)
@observe(type="tool", name="edit_file")
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Edit specific sections of files without full replacement.

    Replaces the FIRST occurrence of `old_text` with `new_text`.
    Be specific with `old_text` to ensure you match the correct section.
    Write access is restricted to agent_workspace/ only for safety.

    Args:
        path: Path to the file to edit (must be in agent_workspace/)
        old_text: The exact text segment to replace
        new_text: The new text to insert in its place

    Returns:
        Success message or error if old_text not found
    """
    try:
        target_path = validate_path(path, write_mode=True)  # Enforce write restrictions
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
@observe(type="tool", name="file_search")
def file_search(pattern: str, path: str = ".") -> str:
    """Find files matching a pattern (glob).

    Args:
        pattern: Glob pattern (e.g., "*.py", "**/*.md")
        path: Directory to search in (default: current directory)
              Can use relative paths like '../src/rag/research_paper_results_reports/'

    Returns:
        List of matching file paths
    """
    try:
        # Validate and resolve the search path
        search_path = validate_path(path)

        original_cwd = os.getcwd()
        os.chdir(search_path)
        try:
            matches = glob.glob(pattern, recursive=True)
            if not matches:
                return f"No files found matching pattern '{pattern}' in {search_path}"
            return "\n".join(matches)
        finally:
            os.chdir(original_cwd)
    except Exception as e:
        return f"Error searching files: {str(e)}"

@tool(parse_docstring=True)
@observe(type="tool", name="file_content_search")
def file_content_search(pattern: str, file_pattern: str = "*", path: str = ".") -> str:
    """Search file contents for patterns/text (grep).

    Args:
        pattern: Text or regex pattern to search for
        file_pattern: Glob pattern for files to search in (default: *)
        path: Directory to search in (default: current directory)
              Can use relative paths like '../src/rag/research_paper_results_reports/'

    Returns:
        List of matches with line numbers
    """
    try:
        # Validate and resolve the search path
        search_path = validate_path(path)

        original_cwd = os.getcwd()
        os.chdir(search_path)
        try:
            files = glob.glob(file_pattern, recursive=True)
            results = []
            for file_path in files:
                path_obj = Path(file_path)
                if path_obj.is_file():
                    try:
                        lines = path_obj.read_text(encoding="utf-8").splitlines()
                        for i, line in enumerate(lines, 1):
                            if pattern.lower() in line.lower():  # Case-insensitive search
                                # Show relative path from search directory
                                results.append(f"{file_path}:{i}: {line.strip()}")
                    except (UnicodeDecodeError, Exception):
                        pass # Skip binary or unreadable files

            if not results:
                return f"No matches found for pattern '{pattern}' in {search_path}"
            return "\n".join(results[:100]) # Limit output to first 100 matches
        finally:
            os.chdir(original_cwd)
    except Exception as e:
        return f"Error searching content: {str(e)}"


@tool(parse_docstring=True)
@observe(type="tool", name="think_strategically")
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
def load_skill(skill_name: str) -> str:
    """Load an agent skill framework for advanced research capabilities.
    
    Agent skills provide structured metacognitive frameworks for:
    - gap_analysis: Identifying missing evidence, contradictions, unexplored areas
    - insight_generation: Synthesizing connections, generating hypotheses
    - research_progression: Tracking investigation across sessions
    
    Args:
        skill_name: Name of skill to load (gap_analysis, insight_generation, research_progression)
    
    Returns:
        Full skill content with framework, structured questions, templates, and examples
    """
    from pathlib import Path
    
    # Get path to agent_skills directory
    skills_dir = Path(__file__).parent.parent.parent / "agent_skills"
    skill_path = skills_dir / f"{skill_name}.md"
    
    if not skill_path.exists():
        available = ["gap_analysis", "insight_generation", "research_progression"]
        return f"Skill '{skill_name}' not found. Available skills: {', '.join(available)}"
    
    try:
        return skill_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error loading skill '{skill_name}': {str(e)}"


@tool(parse_docstring=True)
@observe(type="tool", name="execute_bash")
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
        model: The language model to use for all sub-agents (default)
        state_schema: The state schema (typically DeepAgentState)
        researcher_model: Optional separate model for internet_researcher agent (defaults to model if not provided)

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
            # All other subagents use the default model (subagent_model)
            agent_model = model

        # Create sub-agent with parallel tool calls disabled
        agents[_agent["name"]] = create_react_agent(
            agent_model.bind(parallel_tool_calls=False),
            prompt=_agent["prompt"],
            tools=_tools,
            state_schema=state_schema,
        )

    # Generate description of available sub-agents for the tool description
    other_agents_string = [
        f"- {_agent['name']}: {_agent['description']}" for _agent in subagents
    ]

    @tool(description=prompts.TASK_DESCRIPTION_PREFIX.format(other_agents=other_agents_string))
    @observe(type="tool", name="task_delegation")
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
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            f"Error: invoked agent of type {subagent_type}, the only allowed types are {[f'`{k}`' for k in agents]}",
                            tool_call_id=tool_call_id
                        )
                    ]
                }
            )

        try:
            # Get the requested sub-agent
            sub_agent = agents[subagent_type]

            # Create isolated context with only the task description
            # This is the key to context isolation - no parent history
            state["messages"] = [{"role": "user", "content": description}]

            # Execute the sub-agent in isolation (async)
            result = await sub_agent.ainvoke(state, config={"recursion_limit": 100})

            # Extract the final message from sub-agent
            if not result.get("messages"):
                raise ValueError("Sub-agent returned no messages")
            
            final_message = result["messages"][-1]
            
            # Get content from the final message
            if hasattr(final_message, "content"):
                content = final_message.content
            elif isinstance(final_message, dict):
                content = final_message.get("content", "")
            else:
                content = str(final_message)
            
            # ====== FIX: ENSURE CONTENT IS ALWAYS A STRING ======
            # Convert content to string if it's not already
            if not isinstance(content, str):
                import json
                try:
                    # Try to serialize as JSON for structured data
                    content = json.dumps(content, indent=2, ensure_ascii=False)
                except (TypeError, ValueError):
                    # Fall back to string conversion
                    content = str(content)
            
            # Ensure we have non-empty content
            if not content or not content.strip():
                content = f"Sub-agent {subagent_type} completed but returned empty response"
            # =====================================================

            # Return results to parent agent via Command state update
            return Command(
                update={
                    "messages": [
                        # Sub-agent result becomes a ToolMessage in parent context
                        ToolMessage(
                            content,  # Now guaranteed to be a string
                            tool_call_id=tool_call_id
                        )
                    ],
                }
            )
        
        except Exception as e:
            # If sub-agent fails, return error as ToolMessage to maintain valid chat history
            import traceback
            error_msg = f"Error executing {subagent_type} sub-agent: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            return Command(
                update={
                    "messages": [
                        ToolMessage(
                            error_msg,
                            tool_call_id=tool_call_id
                        )
                    ]
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
        name="filesystem_reader",
        description="File system reader - reads existing files, lists directories, searches content. Use for gathering context from existing documents.",
        prompt=prompts.FILESYSTEM_READER_PROMPT,
        tools=["list_directory", "read_file", "file_search", "file_content_search"],
    ),
    SubAgent(
        name="script_executor",
        description="Script execution specialist - runs Python scripts from src/scripts_for_agent/, converts markdown to PDF, executes bash commands, and creates data visualizations",
        prompt=prompts.SCRIPT_EXECUTOR_PROMPT,
        tools=["execute_bash", "list_directory", "read_file", "write_file", "file_search"],
    ),
    SubAgent(
        name="biomedical_researcher",
        description="Research knowledge base specialist - queries knowledge graph built from research papers using multiple search modes (global, local, hybrid, naive)",
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
        model: The language model to use for all sub-agents (default)
        researcher_model: Optional separate model for internet_researcher agent (defaults to model if not provided)
        subagents: Optional list of SubAgent configurations. If not provided, uses SUB_AGENTS
        tools: Optional list of tools available to sub-agents. If not provided, uses ALL_TOOLS

    Returns:
        The task delegation tool configured with the specified sub-agents
        
    Example:
        # Use default sub-agents with same model for all
        task_tool = create_task_delegation_tool(model)
        
        # Use custom sub-agents with different model for researcher
        custom_agents = [
            {
                "name": "researcher",
                "description": "Research specialist",
                "prompt": RESEARCHER_PROMPT,
                "tools": ["web_search", "think_strategically"]
            }
        ]
        task_tool = create_task_delegation_tool(
            model=subagent_llm,
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

# Main Agent Tools (Orchestration + Writing)
# The main agent plans, delegates context-gathering, and writes outputs directly
MAIN_AGENT_TOOLS: List[Callable[..., Any]] = [
    read_todos,
    write_todos,
    think_strategically,
    load_skill,  # Direct access to agent skills
    # Write tools - main agent handles all writing/editing directly
    write_file,
    edit_file,
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
