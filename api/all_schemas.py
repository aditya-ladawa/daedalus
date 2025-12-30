
from pydantic import BaseModel
from typing_extensions import TypedDict, NotRequired, Literal
from langgraph.prebuilt.chat_agent_executor import AgentState



# Pydantic Models
class ConversationCreate(BaseModel):
    initial_message: str


class ConversationRename(BaseModel):
    title: str


class FileRename(BaseModel):
    new_name: str
    
    
# Deep Agent State
class Todo(TypedDict):
    """A structured task item for tracking progress through complex workflows.

    Attributes:
        content: Short, specific description of the task
        status: Current state - pending, in_progress, or completed
    """
    content: str
    status: Literal["pending", "in_progress", "completed"]


class DeepAgentState(AgentState):
    """Agent state with scratchpad (todos) for complex workflow tracking."""
    todos: NotRequired[list[Todo]]
