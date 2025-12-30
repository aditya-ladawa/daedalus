
from tavily import TavilyClient
import os
from langchain.tools import tool

from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.graph import Command

from dotenv import load_dotenv

load_dotenv()



tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))


@tool
def web_search(query: str) -> str:
    """
    Search the web for current information on any topic.
    
    Args:
        query: The search query to look up.
    
    Returns:
        Search results with relevant information.
    """
    response = tavily_client.search(query, max_results=5)
    
    # Format results
    results = []
    for result in response.get("results", []):
        results.append(f"**{result['title']}**\n{result['content']}\nURL: {result['url']}\n")
    
    return "\n---\n".join(results) if results else "No results found."



    
# # Todo tools

@tool(parse_docstring=True)
def read_todos(
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """Read the current todo list from the agent state.

    This tool allows the agent to retrieve and review the current todo list
    to stay focused on remaining tasks and track progress through complex workflows.

    Args:
        state: Injected agent state containing the current todo list
        tool_call_id: Injected tool call identifier for message tracking

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
    todos: list[Todo], 
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Create or update the agent's todo list for task planning and tracking.

    Args:
        todos: List of todo items with content and status
        tool_call_id: Tool call identifier for message response

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



@tool(parse_docstring=True)
def think_strategically(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?
    - How complex is the question: Have I reached the number of search limits?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"