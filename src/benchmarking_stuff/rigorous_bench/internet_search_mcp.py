"""Wikipedia and Tavily MCP Integration for LangChain Agents

Uses langchain-mcp-adapters to load tools from Wikipedia and Tavily MCP servers.
"""

from langchain_mcp_adapters.client import MultiServerMCPClient


async def get_mcp_tools():
    """Load tools from Wikipedia and Tavily MCP servers asynchronously.
    
    Returns:
        List of LangChain-compatible tool objects
    """
    # Configure MCP servers
    client = MultiServerMCPClient(
        {
            # Wikipedia MCP server (local stdio) - COMMENTED OUT
            # "wikipedia": {
            #     "command": "wikipedia-mcp",
            #     "args": [],
            #     "transport": "stdio",
            # },
            # Tavily MCP server (remote HTTP)
            "tavily": {
                "url": "https://mcp.tavily.com/mcp/?tavilyApiKey=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",
                "transport": "http",
            }
        }
    )
    
    # Get all tools from both servers
    tools = await client.get_tools()
    
    return tools
