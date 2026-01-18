"""Basic ReAct Agent for RigorousBench Baseline Evaluation.

This is a simple LangGraph ReAct agent without subagents or complex orchestration.
Used as a baseline to compare against the deep_agent.py architecture.

Architecture:
- Single ReAct agent (DeepSeek)
- Direct tool access (web_search, file operations)
- No task delegation, no subagents
- Saves reports to basic_agent_reports/
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

from bench_tools import web_search

load_dotenv()


# Basic tools for the ReAct agent
def create_basic_tools(query_id: str):
    """Create simple tools for report writing."""
    from langchain_core.tools import tool
    
    reports_dir = Path(__file__).parent / "basic_agent_reports" / query_id
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
    
    return [web_search, write_report, read_report, read_report_lines]


async def run_query(
    query: str,
    query_id: str,
    model: str = "deepseek-chat",
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
    llm = ChatOpenAI(
        model=model,
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
        temperature=0.0,
    )
    
    # Create tools
    tools = create_basic_tools(query_id)
    
    # Create ReAct agent
    agent = create_react_agent(llm, tools)
    
    # System prompt for the agent
    system_message = """You are a research assistant. Your task is to:

1. Research the query thoroughly using web_search
2. Gather comprehensive information from multiple sources
3. Write a detailed markdown report with:
   - Clear structure (Introduction, Main sections, Conclusion)
   - Inline citations [1], [2], etc.
   - A References section at the end with FULL URLs in markdown format
4. Use write_report to save your final report

**CRITICAL CITATION REQUIREMENTS:**
- Every factual claim MUST have an inline citation [1], [2], etc.
- The References section MUST use this exact format:
  [1] Source Title - https://full-url-here.com/path
  [2] Another Source - https://another-url.com/page
- ALWAYS include the complete URL (starting with https://)
- Prefer authoritative sources (.org, .gov, official documentation sites)
- If citing RFCs, use official RFC Editor or IETF Datatracker URLs

Example References section:
## References
[1] RFC 9000: QUIC Transport Protocol - https://www.rfc-editor.org/rfc/rfc9000
[2] IETF QUIC Working Group - https://datatracker.ietf.org/wg/quic/

Be thorough, cite your sources with full URLs, and provide specific details."""
    
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
            config={"recursion_limit": 14444}
        ):
            # Capture and print all messages from the event
            for value in event.values():
                if isinstance(value, dict) and "messages" in value:
                    for msg in value["messages"]:
                        if hasattr(msg, "pretty_print"):
                            msg.pretty_print()
                        else:
                            print(f"\n[{msg.type.upper()}] {str(msg.content)[:500]}...")
        
        print(f"{'='*60}\n")
        
        report_path = Path(__file__).parent / "basic_agent_reports" / query_id / "report.md"
        return report_path
        
    except Exception as e:
        print(f"❌ Agent error: {e}")
        raise


async def main():
    """Test the basic agent."""
    query = "The QUIC transport protocol was published in May 2021. Summarize its standardization path."
    query_id = "07001"
    
    report_path = await run_query(query, query_id)
    print(f"✓ Report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
