"""Define the state structures for the agent."""

from __future__ import annotations

from typing import Literal, Sequence
from typing_extensions import Annotated, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.prebuilt.chat_agent_executor import AgentState


class Todo(TypedDict):
    """A structured task item for tracking progress through complex workflows.

    Attributes:
        content: Short, specific description of the task
        status: Current state - pending, in_progress, or completed
    """

    content: str
    status: Literal["pending", "in_progress", "completed"]


class InputState(TypedDict):
    """Defines the input state for the agent, representing a narrower interface to the outside world.

    This class is used to define the initial state and structure of incoming data.
    Only messages are exposed externally to keep the frontend interface clean.
    """

    messages: Annotated[Sequence[AnyMessage], add_messages]
    """
    Messages tracking the primary execution state of the agent.

    Typically accumulates a pattern of:
    1. HumanMessage - user input
    2. AIMessage with .tool_calls - agent picking tool(s) to use to collect information
    3. ToolMessage(s) - the responses (or errors) from the executed tools
    4. AIMessage without .tool_calls - agent responding in unstructured format to the user
    5. HumanMessage - user responds with the next conversational turn

    Steps 2-5 may repeat as needed.

    The `add_messages` annotation ensures that new messages are merged with existing ones,
    updating by ID to maintain an "append-only" state unless a message with the same ID is provided.
    """


class DeepAgentState(AgentState):
    """Agent state with scratchpad (todos) for complex workflow tracking.
    
    Extends AgentState which provides:
    - messages: List of conversation messages
    - remaining_steps: Managed field for recursion control
    
    Adds:
    - todos: Optional task tracking for complex workflows
    - files: Optional file storage for context management
    """

    todos: NotRequired[list[Todo]]
    """Optional todo list for tracking multi-step tasks and progress."""

    files: NotRequired[dict[str, str]]
    """Optional file storage for context management and code generation."""


# Keep the old State name for backward compatibility
State = DeepAgentState
