"""Basic ReAct Agent for RigorousBench Baseline Evaluation.

This is a simple LangGraph ReAct agent without subagents or complex orchestration.
Used as a baseline to compare against the deep_agent.py architecture.

Architecture:
- Single ReAct agent
- Direct tool access (web_search, file operations)
- No task delegation, no subagents
- Saves reports to basic_agent_eval_reports/
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# Import shared config
# Import shared config
try:
    from .config import (
        BASIC_AGENT_MODEL,
        BASIC_AGENT_BASE_URL,
        BASIC_AGENT_TEMPERATURE,
        DEEPSEEK_API_KEY,
        GEMINI_API_KEY,
        
    )
    from .tools import web_search
    from .prompts_basic_agent import SYSTEM_PROMPT
except ImportError:
    sys.path.append(str(Path(__file__).parent))
    from config import (
        BASIC_AGENT_MODEL,
        BASIC_AGENT_BASE_URL,
        BASIC_AGENT_TEMPERATURE,
        DEEPSEEK_API_KEY,
    )
    from tools import web_search
    from prompts_basic_agent import SYSTEM_PROMPT

load_dotenv()


# Basic tools for the ReAct agent
def create_basic_tools(query_id: str):
    """Create simple tools for report writing."""
    
    # Use the new directory name
    reports_dir = Path(__file__).parent.parent / "eval_reports" / "rigorous_bench" / "basic_agent" / query_id
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "report.md"
    
    @tool
    def write_report(content: str) -> str:
        """Write the final research report to a markdown file.
        
        Args:
            content: The complete markdown report content
            
        Returns:
            Confirmation message
        """
        report_path.write_text(content)
        return f"✓ Report written to {report_path} ({len(content)} chars)"
    
    @tool
    def read_report() -> str:
        """Read the current report content.
        
        Returns:
            Current report content or message if file doesn't exist
        """
        if report_path.exists():
            return report_path.read_text()
        return "No report exists yet. Use write_report to create one."
    
    @tool
    def read_report_lines(start_line: int = 1, end_line: int = -1) -> str:
        """Read specific lines from the report for review.
        
        Args:
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (-1 for end of file)
            
        Returns:
            Specified lines from the report with line numbers
        """
        if not report_path.exists():
            return "No report exists yet."
        
        lines = report_path.read_text().split('\n')
        
        if end_line == -1:
            end_line = len(lines)
        
        # Clamp values
        start_line = max(1, start_line)
        end_line = min(len(lines), end_line)
        
        # Format with line numbers
        result = f"Lines {start_line}-{end_line} (total {len(lines)} lines):\n\n"
        for i in range(start_line - 1, end_line):
            result += f"{i + 1:4d}: {lines[i]}\n"
        
        return result
    
    @tool
    def edit_report(old_text: str, new_text: str) -> str:
        """Edit a specific section of the report by replacing text.
        
        Args:
            old_text: Exact text to find and replace
            new_text: New text to insert
            
        Returns:
            Success message or error
        """
        if not report_path.exists():
            return "Error: Report does not exist yet."
            
        content = report_path.read_text()
        if old_text not in content:
            return "Error: old_text not found in report."
            
        new_content = content.replace(old_text, new_text, 1)
        report_path.write_text(new_content)
        return f"✓ Replaced text. New size: {len(new_content)} chars"

    return [web_search, write_report, read_report, read_report_lines, edit_report]


async def run_query(
    query: str,
    query_id: str,
    model: str = BASIC_AGENT_MODEL,
):
    """Run a query using the basic ReAct agent.
    
    Args:
        query: The research query
        query_id: Unique identifier for result storage
        model: LLM model to use
        
    Returns:
        Path to the generated report
    """
    # Initialize model
    # llm = ChatOpenAI(
    #     model=model,
    #     api_key=DEEPSEEK_API_KEY,
    #     base_url=BASIC_AGENT_BASE_URL,
    #     temperature=BASIC_AGENT_TEMPERATURE,
    # )
    llm = ChatGoogleGenerativeAI(
        model='gemini-2.5-flash',
        google_api_key=GEMINI_API_KEY,
        temperature=0.0,
        max_tokens=8192,
    )
    
    # Create tools
    tools = create_basic_tools(query_id)
    
    # Create ReAct agent
    agent = create_react_agent(llm, tools)
    
    # System prompt for the agent (No cheat examples)
    system_message = SYSTEM_PROMPT
    
    # Run the agent with streaming
    try:
        print(f"\n{'='*60}")
        print(f"🤖 Basic ReAct Agent - Query: {query_id}")
        print(f"{'='*60}")
        
        async for event in agent.astream(
            {
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": query}
                ]
            },
            config={"recursion_limit": 100},
        ):
            # Print streaming output
            for value in event.values():
                if isinstance(value, dict) and "messages" in value:
                    for msg in value["messages"]:
                        type_str = msg.type.upper() if hasattr(msg, "type") else "MSG"
                        print(f"\n[{type_str}] {str(msg.content)[:200]}...")
        
        print(f"{'='*60}\n")
        
        # Check if report was created
        reports_dir = Path(__file__).parent.parent / "eval_reports" / "rigorous_bench" / "basic_agent" / query_id
        report_path = reports_dir / "report.md"
        
        if report_path.exists():
            print(f"✅ Report generated at: {report_path}")
            return str(report_path)
        else:
            print("❌ Agent finished but no report was written.")
            return None
            
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}\n{traceback.format_exc()}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Basic ReAct baseline agent")
    parser.add_argument("--query", type=str, help="Research query")
    parser.add_argument("--query-id", type=str, default="test_basic", help="Query ID for output")
    parser.add_argument("--model", type=str, default=BASIC_AGENT_MODEL, help="Agent model")
    
    args = parser.parse_args()
    
    if args.query:
        asyncio.run(run_query(args.query, args.query_id, args.model))
    else:
        print("Please provide a --query argument.")
