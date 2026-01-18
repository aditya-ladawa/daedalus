"""RigorousBench Deep Research Agent using LangGraph.

Architecture (mirrors src/agent_graph/):
- Main Agent: DeepSeek (orchestration + report writing section by section)
- Subagents: Gemini 2.5 Flash
  - internet_researcher: Tavily MCP for web research
  - script_executor: Restricted bash (all_reports/ only)
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agent_graph"))
from state import DeepAgentState

from bench_prompts import SYSTEM_PROMPT
from bench_tools import (
    MAIN_AGENT_TOOLS,
    create_task_delegation_tool_async,
)

load_dotenv()


async def build_agent_graph(
    main_model_name: str = "deepseek-chat",
    subagent_model_name: str = "gemini-2.5-flash",
):
    """Build the deep research agent graph.
    
    Args:
        main_model_name: Model for main orchestrator (DeepSeek)
        subagent_model_name: Model for subagents (Gemini)
    
    Returns:
        Compiled LangGraph agent
    """
    # Main agent: DeepSeek for orchestration
    main_model = ChatOpenAI(
        model=main_model_name,
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        temperature=0.3,
        max_tokens=16384,
    )
    
    # Subagent model: Gemini 2.5 Flash
    subagent_model = ChatGoogleGenerativeAI(
        model=subagent_model_name,
        google_api_key=os.environ.get("GEMINI_API_KEY"),
        temperature=0.3,
        max_tokens=8192,
    )
    
    # Create task delegation tool (async to load MCP tools)
    print("🔧 Loading Tavily MCP tools...")
    task_tool = await create_task_delegation_tool_async(model=subagent_model)
    
    # Combine main tools with task delegation
    all_tools = MAIN_AGENT_TOOLS + [task_tool]
    
    print("🧠 Building RigorousBench Agent...")
    print(f"   Main Agent: {main_model_name} (DeepSeek)")
    print(f"   Subagents: {subagent_model_name} (Gemini)")
    print(f"   Main Tools: {len(all_tools)} (includes task delegation)")
    print("   Subagents: internet_researcher (Tavily MCP), script_executor")
    
    # Build main agent
    graph = create_react_agent(
        main_model.bind(parallel_tool_calls=False),
        tools=all_tools,
        state_schema=DeepAgentState,
        prompt=SYSTEM_PROMPT,
    )
    
    # High recursion limit for deep research
    graph = graph.with_config({"recursion_limit": 1000})
    
    print("✅ Agent ready!")
    return graph


async def run_query(
    query: str,
    query_id: str,
    main_model: str = "deepseek-chat",
    subagent_model: str = "gemini-2.5-flash",
):
    """Run a research query and generate report.
    
    Args:
        query: Research question
        query_id: Unique ID (e.g., "07001") for output directory
        main_model: Main agent model (DeepSeek)
        subagent_model: Subagent model (Gemini)
    
    Returns:
        Final response content
    """
    graph = await build_agent_graph(main_model, subagent_model)
    
    # Initial message with query and ID context
    initial_message = f"""Research Query ID: {query_id}

{query}

INSTRUCTIONS:
1. **Analyze Query**: Break down the research question into specific sub-tasks.
2. **Iterative Research**: Use `task` to delegate, then `read_todos` to track.
3. **Section-by-Section**: Write one section, then REVIEW it for completeness.
4. **Granular Detail**: Include exact version numbers, dates, and technical comparisons.
5. **Citations**: Inline citations [N] for every claim are MANDATORY.

Report structure:
- # Title
Report structure:
- # Title
- ## Introduction  
- ## [Body Sections]
- ## Conclusion
- ## References (Full URLs)
- ## [Appendix if needed]

CRITICAL: Save to query_id="{query_id}" using write_report tool.
"""
    
    print(f"\n📝 Processing query {query_id}...")
    
    # Suppress verbose logging
    import logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    
    try:
        # Use astream for real-time output
        print(f"\n{'='*60}")
        print(f"🤖 Agent Stream Output")
        print(f"{'='*60}")
        
        final_messages = []
        final_messages = []
        async for event in graph.astream(
            {"messages": [{"role": "user", "content": initial_message}]},
            config={"recursion_limit": 1000},
        ):
            # Capture all messages from the event
            for value in event.values():
                if isinstance(value, dict) and "messages" in value:
                    for msg in value["messages"]:
                        # Pretty print all messages if possible
                        if hasattr(msg, "pretty_print"):
                            msg.pretty_print()
                        else:
                            # Fallback logging for messages without pretty_print
                            print(f"\n[{msg.type.upper()}] {str(msg.content)[:500]}...")
                        
                        # Store messages for final result extraction
                        final_messages.append(msg)
            
            # Handle end event
            if "__end__" in event:
                final_messages = event["__end__"]["messages"]
        
        print(f"{'='*60}\n")
        
        if not final_messages:
            return "Error: No response from agent"
        
        # Extract final response - iterate through messages to find content
        content = ""
        for msg in reversed(final_messages):
            if hasattr(msg, "content"):
                msg_content = msg.content
                # Handle various content formats
                if isinstance(msg_content, str) and msg_content.strip():
                    content = msg_content
                    break
                elif isinstance(msg_content, list):
                    text_parts = []
                    for p in msg_content:
                        if isinstance(p, dict) and "text" in p:
                            text_parts.append(p["text"])
                        elif isinstance(p, str):
                            text_parts.append(p)
                    if text_parts:
                        content = "\n".join(text_parts)
                        break
        
        print(f"✅ Query {query_id} completed")
        return content if content else "Agent completed but no text content found"
        
    except Exception as e:
        import traceback
        error = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ Query {query_id} failed: {e}")
        return error


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run RigorousBench deep research agent")
    parser.add_argument("--query", type=str, help="Research query")
    parser.add_argument("--query-id", type=str, default="test", help="Query ID for output")
    parser.add_argument("--main-model", type=str, default="deepseek-chat", help="Main agent model")
    parser.add_argument("--subagent-model", type=str, default="gemini-2.5-flash", help="Subagent model")
    
    args = parser.parse_args()
    
    if args.query:
        result = asyncio.run(run_query(
            args.query, args.query_id, args.main_model, args.subagent_model
        ))
        print("\n" + "=" * 60)
        print("FINAL RESPONSE:")
        print("=" * 60)
        print(result)
    else:
        # Demo query
        demo_query = "What were the key milestones in the QUIC protocol standardization process from 2016 to 2021?"
        result = asyncio.run(run_query(demo_query, "demo_quic", args.main_model, args.subagent_model))
        print("\n" + "=" * 60)
        print("DEMO RESPONSE:")
        print("=" * 60)
        print(result[:2000] + "..." if len(result) > 2000 else result)
