"""
DAEDALUS FastAPI Backend
Deep Agent for Exploratory Discovery and Analytical Literature Understanding System

This backend provides:
1. AG-UI/CopilotKit endpoint for the LangGraph agent at "/"
2. File management routes for project files
3. Simple conversation metadata (listing, renaming, deleting)
"""

import warnings
# Suppress Pydantic warnings from ag_ui_langgraph package
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import os
import shutil
import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState

from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

from api.all_schemas import ConversationCreate, ConversationRename, FileRename, DeepAgentState


from uuid_extensions import uuid7
from api.all_tools import web_search, read_todos, write_todos, think_strategically


from dotenv import load_dotenv
load_dotenv()

# Constants
PROJECTS_DIR = Path("projects")

# Initialize chat model at module level
chat_model = init_chat_model(
    model="gemini-3-flash-preview",
    model_provider="google_genai",
    temperature=0.1,
    thinking_level='minimal'
)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize checkpointer and agent on startup, cleanup on shutdown."""
    
    # Ensure projects directory exists
    PROJECTS_DIR.mkdir(exist_ok=True)
    
    # Create the database directory if it doesn't exist
    db_path = os.getenv("SQLITE_DB_PATH", "./data/checkpoints.db")
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    
    # Store db_path for use by routes
    app.state.db_path = db_path
    
    # Create conversations table in the same database
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        await db.commit()
    
    # Initialize AsyncSqliteSaver and create agent
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        await checkpointer.setup()
        
        app.state.checkpointer = checkpointer
        
        # Create the ReAct agent with LangGraph
        graph = create_agent(
            model=chat_model,
            tools=[web_search, read_todos, write_todos, think_strategically],
            checkpointer=checkpointer,
            state=DeepAgentState
        )
        
        # Add the CopilotKit AG-UI endpoint at root
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


# Initialize FastAPI with lifespan
app = FastAPI(
    title="DAEDALUS API",
    description="Deep Agent for Exploratory Discovery and Analytical Literature Understanding System",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Conversation Metadata Routes (for UI listing/management only)
# Actual chat is handled by CopilotKit through the AG-UI endpoint
# =============================================================================

@app.get("/conversations")
async def list_conversations(request: Request):
    """List all conversations with their titles and timestamps."""
    db_path = request.app.state.db_path
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        
        conversations = [
            {
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]
    
    return {"conversations": conversations}


@app.post("/conversations")
async def create_conversation(data: ConversationCreate, request: Request):
    """Create a new conversation with auto-generated title."""
    db_path = request.app.state.db_path
    
    # Generate UUIDv7 for conversation ID
    chat_id = str(uuid7())
    
    # Create project directory
    project_path = PROJECTS_DIR / chat_id
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Generate title using chat model
    title_prompt = f"Generate a short, concise title (max 6 words) for a conversation that starts with: '{data.initial_message}'. Return ONLY the title, nothing else."
    title_response = await chat_model.ainvoke(title_prompt)
    
    # Extract text from response
    content = title_response.content
    if isinstance(content, str):
        title = content.strip().strip('"\'')
    elif isinstance(content, list):
        # Handle list of content blocks
        title = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ).strip().strip('"\'')
    else:
        title = str(content).strip().strip('"\'')
    
    # Limit title length
    if len(title) > 60:
        title = title[:57] + "..."
    
    # Save to database
    now = datetime.now().timestamp()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (chat_id, title, now, now)
        )
        await db.commit()
    
    return {
        "id": chat_id,
        "title": title
    }


@app.patch("/conversations/{chat_id}")
async def rename_conversation(chat_id: str, data: ConversationRename, request: Request):
    """Rename a conversation."""
    db_path = request.app.state.db_path
    
    async with aiosqlite.connect(db_path) as db:
        # Check if conversation exists
        cursor = await db.execute("SELECT id FROM conversations WHERE id = ?", (chat_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update title and updated_at
        now = datetime.now().timestamp()
        await db.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (data.title, now, chat_id)
        )
        await db.commit()
    
    return {"id": chat_id, "title": data.title}


@app.delete("/conversations/{chat_id}")
async def delete_conversation(chat_id: str, request: Request):
    """Delete a conversation and its project directory."""
    db_path = request.app.state.db_path
    
    # Delete from database
    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM conversations WHERE id = ?", (chat_id,))
        await db.commit()
    
    # Delete project directory
    project_path = PROJECTS_DIR / chat_id
    if project_path.exists():
        shutil.rmtree(project_path)
    
    return {"status": "deleted", "id": chat_id}


@app.get("/conversations/{chat_id}/metadata")
async def get_conversation_metadata(chat_id: str, request: Request):
    """Get conversation metadata (title, etc)."""
    db_path = request.app.state.db_path
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (chat_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }


# =============================================================================
# File Management Routes
# =============================================================================

@app.get("/conversations/{chat_id}/files")
async def list_files(chat_id: str):
    """List all files in a conversation's project directory."""
    project_path = PROJECTS_DIR / chat_id
    if not project_path.exists():
        # Create the directory if it doesn't exist (new conversation)
        project_path.mkdir(parents=True, exist_ok=True)
    
    files = []
    for file_path in project_path.iterdir():
        if file_path.is_file():
            files.append({
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "extension": file_path.suffix.lower()
            })
    
    return {"files": files}


@app.post("/conversations/{chat_id}/files")
async def upload_file(chat_id: str, file: UploadFile = File(...)):
    """Upload a file to the conversation's project directory."""
    project_path = PROJECTS_DIR / chat_id
    if not project_path.exists():
        project_path.mkdir(parents=True, exist_ok=True)
    
    file_path = project_path / file.filename
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    return {
        "name": file.filename,
        "size": file_path.stat().st_size,
        "extension": file_path.suffix.lower()
    }


@app.get("/conversations/{chat_id}/files/{filename}")
async def get_file(chat_id: str, filename: str):
    """Get a file from the conversation's project directory."""
    project_path = PROJECTS_DIR / chat_id
    file_path = project_path / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, filename=filename)


@app.patch("/conversations/{chat_id}/files/{filename}")
async def rename_file(chat_id: str, filename: str, data: FileRename):
    """Rename a file in the conversation's project directory."""
    project_path = PROJECTS_DIR / chat_id
    old_path = project_path / filename
    new_path = project_path / data.new_name
    
    if not old_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if new_path.exists():
        raise HTTPException(status_code=400, detail="A file with that name already exists")
    
    old_path.rename(new_path)
    
    return {
        "old_name": filename,
        "new_name": data.new_name
    }


@app.delete("/conversations/{chat_id}/files/{filename}")
async def delete_file(chat_id: str, filename: str):
    """Delete a file from the conversation's project directory."""
    project_path = PROJECTS_DIR / chat_id
    file_path = project_path / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path.unlink()
    
    return {"status": "deleted", "name": filename}
