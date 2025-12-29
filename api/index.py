"""
FastAPI server with CopilotKit LangGraph integration using Gemini and AsyncSqliteSaver.
"""

import os
import warnings
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from langchain.agents import create_agent
from pathlib import Path
from langchain.chat_models import init_chat_model
from langchain.tools import tool

    



from tavily import TavilyClient


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




# Load environment variables
load_dotenv()


# Constants
PROJECTS_DIR = Path("projects")
CHECKPOINTS_DB = "checkpoints.sqlite"
graph = None

chat_model = init_chat_model(
    model="gemini-3-flash-preview",
    model_provider="google_genai",
    temperature=0.1,
    thinking_level='minimal'
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to setup and teardown the async SQLite checkpointer.
    """
    global graph
    
    # Create the database directory if it doesn't exist
    db_path = os.getenv("SQLITE_DB_PATH", "./data/checkpoints.db")
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    
    # Setup AsyncSqliteSaver
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        await checkpointer.setup()
        
        # Create the graph with the checkpointer
        app.state.agent = create_agent(
            chat_model,
            tools=[web_search],
            checkpointer=checkpointer
        )
        
        graph = app.state.agent        
        # Add the CopilotKit endpoint
        add_langgraph_fastapi_endpoint(
            app=app,
            agent=LangGraphAGUIAgent(
                name="gemini_agent",
                description="An AI assistant powered by Gemini and LangGraph with persistent memory.",
                graph=graph,
            ),
            path="/",
        )
        
        yield
        
        # Cleanup happens automatically when context manager exits


# Create FastAPI app with lifespan
app = FastAPI(
    title="CopilotKit LangGraph Gemini Agent",
    description="A LangGraph agent with Gemini model and async SQLite persistence",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model": "gemini"}

