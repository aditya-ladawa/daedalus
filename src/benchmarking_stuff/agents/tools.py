"""Shared tools for benchmark agents.

Provides tools for report writing, web search, bash execution, and task delegation.
All file operations are restricted to reports directories to prevent security issues.
"""

import os
import subprocess
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.types import Command
from tavily import TavilyClient
from typing_extensions import TypedDict

load_dotenv()

# =============================================================================
# STATE DEFINITION (for tools that need it)
# =============================================================================

class Todo(TypedDict):
    """Todo item for tracking research progress."""
    content: str
    status: str  # 'pending', 'in_progress', 'completed'


# =============================================================================
# PATH VALIDATION
# =============================================================================

def validate_reports_path(reports_dir: Path, path_str: str, must_exist: bool = False) -> Path:
    """Validate path is within the given reports directory.
    
    Args:
        reports_dir: Base reports directory
        path_str: Path string to validate
        must_exist: If True, path must already exist
        
    Returns:
        Validated absolute path
        
    Raises:
        ValueError: If path is outside reports directory
    """
    path = Path(path_str)
    
    # Make absolute if relative
    if not path.is_absolute():
        full_path = (reports_dir / path).resolve()
    else:
        full_path = path.resolve()
    
    # Must be inside reports_dir
    try:
        full_path.relative_to(reports_dir)
    except ValueError:
        raise ValueError(
            f"Access denied: Path {path_str} is outside reports directory. "
            f"All operations are restricted to: {reports_dir}"
        )
    
    if must_exist and not full_path.exists():
        raise ValueError(f"Path does not exist: {path_str}")
    
    return full_path


# =============================================================================
# REPORT WRITING TOOLS
# =============================================================================

def create_report_tools(reports_dir: Path):
    """Create report management tools for a specific reports directory.
    
    Args:
        reports_dir: Directory where reports will be stored
        
    Returns:
        List of report management tools
    """
    
    @tool(parse_docstring=True)
    def write_report(query_id: str, content: str, filename: str = "report.md") -> str:
        """Write a research report to {query_id}/{filename}.
        
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
            query_dir = reports_dir / query_id
            query_dir.mkdir(parents=True, exist_ok=True)
            
            # Write report
            report_path = query_dir / filename
            report_path.write_text(content, encoding="utf-8")
            
            return f"Successfully wrote {len(content)} characters to {report_path.relative_to(reports_dir.parent)}"
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
            report_path = reports_dir / query_id / filename
            if not report_path.exists():
                return f"Error: Report not found at {query_id}/{filename}"
            
            lines = report_path.read_text(encoding="utf-8").splitlines()
            total_lines = len(lines)
            
            # Clamp to valid range
            start_line = max(1, start_line)
            end_line = min(total_lines, end_line)
            
            result = f"Lines {start_line}-{end_line} of {total_lines}:\\n"
            for i in range(start_line - 1, end_line):
                result += f"{i+1:4d}: {lines[i]}\\n"
            
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
            report_path = reports_dir / query_id / filename
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
            
            return f"Found {len(matches)} matches:\\n" + "\\n".join(matches)
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
            report_path = reports_dir / query_id / filename
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
        """Read a file from the reports directory.
        
        Args:
            path: Path relative to reports directory
        
        Returns:
            File contents
        """
        try:
            full_path = validate_reports_path(reports_dir, path, must_exist=True)
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @tool(parse_docstring=True)
    def list_directory(path: str = ".") -> str:
        """List contents of a directory within reports directory.
        
        Args:
            path: Directory path relative to reports directory
        
        Returns:
            List of files and directories
        """
        try:
            full_path = validate_reports_path(reports_dir, path, must_exist=True)
            if not full_path.is_dir():
                return f"Error: {path} is not a directory"
            
            items = []
            for item in sorted(full_path.iterdir()):
                symbol = "📁" if item.is_dir() else "📄"
                items.append(f"{symbol} {item.name}")
            
            return "\\n".join(items) if items else "(empty directory)"
        except Exception as e:
            return f"Error listing directory: {str(e)}"

    return [write_report, read_report_lines, grep_report, edit_report, read_file, list_directory]


# =============================================================================
# BASH EXECUTOR
# =============================================================================

def create_bash_tool(reports_dir: Path, project_root: Path):
    """Create restricted bash execution tool.
    
    Args:
        reports_dir: Directory where bash commands will be executed
        project_root: Project root for finding .venv
        
    Returns:
        Bash execution tool
    """
    
    @tool(parse_docstring=True)
    def execute_bash_restricted(
        command: str,
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> str:
        """Execute bash commands RESTRICTED to reports directory only.
        
        The virtual environment (.venv) is automatically activated.
        Working directory is set to the reports directory.
        
        Security restrictions:
        - Can ONLY access files within reports directory
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
            os.chdir(reports_dir)
            
            # Activate virtual environment
            venv_activate = project_root / ".venv" / "bin" / "activate"
            if venv_activate.exists():
                command = f"source {venv_activate} && {command}"
            
            result = subprocess.run(
                command,
                shell=True,
                executable='/bin/bash',
                capture_output=True,
                text=True,
                timeout=60,  # 1 minute timeout
                cwd=str(reports_dir),
            )
            
            os.chdir(original_dir)
            
            output = result.stdout
            if result.stderr:
                output += f"\\n[STDERR]\\n{result.stderr}"
            
            if result.returncode != 0:
                output = f"Command failed (exit {result.returncode})\\n{output}"
            
            return output if output.strip() else "Command executed (no output)"
            
        except subprocess.TimeoutExpired:
            os.chdir(original_dir)
            return "Error: Command timed out after 60 seconds"
        except Exception as e:
            os.chdir(original_dir)
            return f"Error: {str(e)}"
    
    return execute_bash_restricted


# =============================================================================
# TODO MANAGEMENT
# =============================================================================

@tool
def read_todos(
    state: Annotated[dict, "InjectedState"],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """Read the current todo list from agent state.
    
    Returns:
        Formatted todo list
    """
    todos = state.get("todos", [])
    if not todos:
        return "No todos in the list."
    
    result = "Current TODOs:\\n"
    for i, todo in enumerate(todos, 1):
        emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(
            todo["status"], "❓"
        )
        result += f"{i}. {emoji} {todo['content']} ({todo['status']})\\n"
    
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
# STRATEGIC THINKING
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
# WEB SEARCH
# =============================================================================

# Initialize Tavily client
tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))


@tool(parse_docstring=True)
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
        max_results=9,
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
        result_text = f"**Result {idx}: {title}**\\n"
        result_text += f"Relevance Score: {score:.3f}\\n"
        result_text += f"{content}\\n"
        result_text += f"Source: {url}\\n"

        results.append(result_text)

    if not results:
        return "No results found."

    # Combine results with a references section
    output = "\\n---\\n".join(results)
    output += "\\n\\n" + "="*60 + "\\n"
    output += "**🔗 REFERENCES (Include these in your final output):**\\n"
    output += "\\n".join(source_urls)
    output += "\\n" + "="*60 + "\\n"

    return output
