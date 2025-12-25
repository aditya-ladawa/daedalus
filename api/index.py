"""
DAEDALUS FastAPI Backend
Deep Agent for Exploratory Discovery and Analytical Literature Understanding System
"""

import os
import json
import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from uuid_extensions import uuid7
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Constants
PROJECTS_DIR = Path("projects")
CHECKPOINTS_DB = "checkpoints.sqlite"


def extract_text(content) -> str:
    """Extract text from message content, handling both string and list formats."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict):
                if part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif "text" in part and part.get("type") not in ("thought", "thinking"):
                    text_parts.append(part["text"])
            elif hasattr(part, "text"):
                if getattr(part, "type", "text") in ("text", "content"):
                    text_parts.append(part.text)
        return "".join(text_parts)
    return str(content) if content is not None else ""


# Pydantic Models
class MessageRequest(BaseModel):
    message: str


class ConversationCreate(BaseModel):
    initial_message: str


class ConversationRename(BaseModel):
    title: str


class FileRename(BaseModel):
    new_name: str


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize chat model and checkpointer on startup, cleanup on shutdown."""
    # Ensure projects directory exists
    PROJECTS_DIR.mkdir(exist_ok=True)
    
    # Initialize chat model
    app.state.chat_model = init_chat_model(
        model="gemini-3-flash-preview",
        model_provider="google_genai",
        temperature=0.1,
        thinking_level='minimal'
    )
    
    # Initialize AsyncSqliteSaver and create agent
    async with AsyncSqliteSaver.from_conn_string(CHECKPOINTS_DB) as saver:
        await saver.setup()
        app.state.checkpointer = saver
        app.state.agent = create_agent(
            app.state.chat_model,
            tools=[],
            checkpointer=saver
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


@app.get("/healthcheck")
async def healthcheck():
    """Health check endpoint."""
    return {"status": "healthy", "service": "DAEDALUS"}


# =============================================================================
# Conversation Routes
# =============================================================================

@app.get("/conversations")
async def list_conversations(request: Request):
    """List all conversations with their titles and timestamps."""
    conversations = []
    
    # Get all thread configs from checkpointer
    checkpointer = request.app.state.checkpointer
    
    # List all project directories to find conversation IDs
    if PROJECTS_DIR.exists():
        for project_dir in PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                chat_id = project_dir.name
                
                # Use directory creation time for created_at
                created_at = project_dir.stat().st_ctime
                
                # Get last active time from directory modification
                updated_at = project_dir.stat().st_mtime
                
                # Try to get metadata from checkpoint
                config = {"configurable": {"thread_id": chat_id}}
                try:
                    checkpoint_tuple = await checkpointer.aget_tuple(config)
                    title = "Untitled"
                    if checkpoint_tuple and checkpoint_tuple.metadata:
                        title = checkpoint_tuple.metadata.get("title", "Untitled")
                    
                    conversations.append({
                        "id": chat_id,
                        "title": title,
                        "created_at": created_at,
                        "updated_at": updated_at
                    })
                except Exception:
                    conversations.append({
                        "id": chat_id,
                        "title": "Untitled",
                        "created_at": created_at,
                        "updated_at": updated_at
                    })
    
    # Sort by updated_at descending
    conversations.sort(key=lambda x: x["updated_at"], reverse=True)
    
    return {"conversations": conversations}


@app.post("/conversations")
async def create_conversation(data: ConversationCreate, request: Request):
    """Create a new conversation with auto-generated title."""
    # Generate UUIDv7 for conversation ID
    chat_id = str(uuid7())
    
    # Create project directory
    project_path = PROJECTS_DIR / chat_id
    project_path.mkdir(parents=True, exist_ok=True)
    
    # Generate title using chat model
    chat_model = request.app.state.chat_model
    title_prompt = f"Generate a short, concise title (max 6 words) for a conversation that starts with: '{data.initial_message}'. Return ONLY the title, nothing else."
    title_response = await chat_model.ainvoke(title_prompt)
    title = extract_text(title_response.content).strip().strip('"\'')
    
    # Invoke agent with initial message and store title in metadata
    agent = request.app.state.agent
    config = {
        "configurable": {"thread_id": chat_id},
        "metadata": {"title": title}
    }
    
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": data.initial_message}]},
        config
    )
    
    # Extract assistant response
    assistant_message = ""
    if response and "messages" in response:
        for msg in reversed(response["messages"]):
            if hasattr(msg, "type") and msg.type == "ai":
                assistant_message = extract_text(msg.content)
                break
            elif isinstance(msg, dict) and msg.get("role") == "assistant":
                assistant_message = extract_text(msg.get("content", ""))
                break
    
    return {
        "id": chat_id,
        "title": title,
        "response": assistant_message
    }


@app.get("/conversations/{chat_id}")
async def get_conversation(chat_id: str, request: Request):
    """Get conversation history."""
    config = {"configurable": {"thread_id": chat_id}}
    checkpointer = request.app.state.checkpointer
    
    # Get checkpoint
    checkpoint_tuple = await checkpointer.aget_tuple(config)
    if not checkpoint_tuple:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Extract messages from checkpoint
    messages = []
    if checkpoint_tuple.checkpoint:
        channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
        msgs = channel_values.get("messages", [])
        for msg in msgs:
            if hasattr(msg, "type"):
                messages.append({
                    "role": "user" if msg.type == "human" else "assistant",
                    "content": extract_text(msg.content)
                })
            elif isinstance(msg, dict):
                messages.append({
                    "role": msg.get("role", "unknown"),
                    "content": extract_text(msg.get("content", ""))
                })
    
    title = checkpoint_tuple.metadata.get("title", "Untitled") if checkpoint_tuple.metadata else "Untitled"
    
    return {
        "id": chat_id,
        "title": title,
        "messages": messages
    }


@app.post("/conversations/{chat_id}")
async def send_message(chat_id: str, data: MessageRequest, request: Request):
    """Send a message to continue the conversation."""
    # Check if conversation exists
    project_path = PROJECTS_DIR / chat_id
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get existing metadata to preserve title
    checkpointer = request.app.state.checkpointer
    config = {"configurable": {"thread_id": chat_id}}
    checkpoint_tuple = await checkpointer.aget_tuple(config)
    
    title = "Untitled"
    if checkpoint_tuple and checkpoint_tuple.metadata:
        title = checkpoint_tuple.metadata.get("title", "Untitled")
    
    # Invoke agent with new message
    agent = request.app.state.agent
    config_with_meta = {
        "configurable": {"thread_id": chat_id},
        "metadata": {"title": title}
    }
    
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": data.message}]},
        config_with_meta
    )
    
    # Extract assistant response
    assistant_message = ""
    if response and "messages" in response:
        for msg in reversed(response["messages"]):
            if hasattr(msg, "type") and msg.type == "ai":
                assistant_message = extract_text(msg.content)
                break
            elif isinstance(msg, dict) and msg.get("role") == "assistant":
                assistant_message = extract_text(msg.get("content", ""))
                break
    
    return {"response": assistant_message}


@app.patch("/conversations/{chat_id}")
async def rename_conversation(chat_id: str, data: ConversationRename, request: Request):
    """Rename a conversation."""
    checkpointer = request.app.state.checkpointer
    config = {"configurable": {"thread_id": chat_id}}
    
    # Get existing checkpoint
    checkpoint_tuple = await checkpointer.aget_tuple(config)
    if not checkpoint_tuple:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Ensure config has all required fields for aput
    full_config = checkpoint_tuple.config.copy()
    if "configurable" not in full_config:
        full_config["configurable"] = {}
    if "checkpoint_ns" not in full_config["configurable"]:
        full_config["configurable"]["checkpoint_ns"] = ""
    
    # Update metadata with new title
    new_metadata = checkpoint_tuple.metadata.copy() if checkpoint_tuple.metadata else {}
    new_metadata["title"] = data.title
    
    # Save updated checkpoint with new metadata
    await checkpointer.aput(
        full_config,
        checkpoint_tuple.checkpoint,
        new_metadata,
        {}
    )
    
    return {"id": chat_id, "title": data.title}


@app.delete("/conversations/{chat_id}")
async def delete_conversation(chat_id: str, request: Request):
    """Delete a conversation and its project directory."""
    # Delete project directory
    project_path = PROJECTS_DIR / chat_id
    if project_path.exists():
        shutil.rmtree(project_path)
    
    # Delete checkpoints
    checkpointer = request.app.state.checkpointer
    await checkpointer.adelete_thread(chat_id)
    
    return {"status": "deleted", "id": chat_id}


# =============================================================================
# File Management Routes
# =============================================================================

@app.get("/conversations/{chat_id}/files")
async def list_files(chat_id: str):
    """List all files in a conversation's project directory."""
    project_path = PROJECTS_DIR / chat_id
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    
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
        raise HTTPException(status_code=404, detail="Conversation not found")
    
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
