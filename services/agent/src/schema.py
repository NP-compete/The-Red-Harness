"""Schema definitions for the template agent."""

from typing import Any, Literal, NotRequired

from pydantic import BaseModel, Field, field_validator
from typing_extensions import TypedDict


class UserInput(BaseModel):
    """Basic user input model for agent interactions."""

    message: str = Field(
        description="User input message to be processed by the agent.",
        examples=["What is 2 multiplied by 3?"],
    )
    thread_id: str | None = Field(
        description="Thread ID to persist and continue a multi-turn conversation. Auto-generated if not provided.",
        default=None,
        examples=["847c6285-8fc9-4560-a83f-4e6285809254"],
    )
    session_id: str | None = Field(
        description="Session ID to persist and continue a conversation across multiple threads.",
        default=None,
        examples=["847c6285-8fc9-4560-a83f-4e6285809254"],
    )
    user_id: str | None = Field(
        description="User ID to persist and continue a conversation across multiple threads.",
        default=None,
        examples=["847c6285-8fc9-4560-a83f-4e6285809254"],
    )


class StreamRequest(UserInput):
    """User input model for streaming agent responses."""

    stream_tokens: bool = Field(
        description="Whether to stream LLM tokens to the client in real-time.",
        default=True,
    )


class ToolCall(TypedDict):
    """Represents a request to call a tool."""

    name: str
    """The name of the tool to be called."""
    args: dict[str, Any]
    """The arguments to pass to the tool call."""
    id: str | None
    """An optional identifier associated with the tool call."""
    type: NotRequired[Literal["tool_call"]]
    """The type identifier for tool calls."""


class ChatMessage(BaseModel):
    """Message model for chat conversations."""

    type: Literal["human", "ai", "tool", "custom"] = Field(
        description="The role or type of the message in the conversation.",
        examples=["human", "ai", "tool", "custom"],
    )
    content: str = Field(
        description="The text content of the message.",
        examples=["Hello, world!"],
    )
    tool_calls: list[ToolCall] = Field(
        description="Tool calls included in this message.",
        default=[],
    )
    tool_call_id: str | None = Field(
        description="ID of the tool call that this message is responding to.",
        default=None,
        examples=["call_Jja7J89XsjrOLA5r!MEOW!SL"],
    )
    status: str | None = Field(
        description="Status of a tool message result (e.g. 'success' or 'error').",
        default=None,
    )
    run_id: str | None = Field(
        description="Run ID associated with this message for tracking (hex format).",
        default=None,
        examples=["847c62858fc94560a83f4e6285809254"],
    )
    trace_id: str | None = Field(
        description="Trace ID associated with this message for tracing (hex format).",
        default=None,
        examples=["847c62858fc94560a83f4e6285809254"],
    )
    thread_id: str | None = Field(
        description="Thread ID associated with this message for conversation tracking (hex format).",
        default=None,
        examples=["847c62858fc94560a83f4e6285809254"],
    )
    session_id: str | None = Field(
        description="Session ID associated with this message for session tracking (hex format).",
        default=None,
        examples=["847c62858fc94560a83f4e6285809254"],
    )
    response_metadata: dict[str, Any] = Field(
        description="Additional metadata for the response, such as headers, logprobs, or token counts.",
        default={},
    )
    custom_data: dict[str, Any] = Field(
        description="Custom data associated with this message.",
        default={},
    )


class FeedbackRequest(BaseModel):
    """Feedback model for recording user feedback to LangFuse."""

    trace_id: str = Field(
        description="Trace ID to record feedback for (hex format, no hyphens).",
        examples=["847c62858fc94560a83f4e6285809254"],
    )
    name: str = Field(
        description="Score name/identifier.",
        examples=["user-rating", "thumbs-up"],
    )
    value: float = Field(
        description="Score value.",
        examples=[0.8, 1.0],
    )
    kwargs: dict[str, Any] = Field(
        description="Additional feedback parameters passed to LangFuse.",
        default={},
        examples=[{"comment": "In-line human feedback"}],
    )
    thread_id: str | None = Field(
        default=None,
        description="Thread ID for persistence",
    )
    message_id: str | None = Field(
        default=None,
        description="Message ID for persistence",
    )
    user_id: str | None = Field(
        default=None,
        description="User ID for persistence",
    )


class FeedbackResponse(BaseModel):
    """Response model for feedback operations."""

    status: Literal["success"] = "success"


class ChatHistoryResponse(BaseModel):
    """Response model for chat history requests."""

    messages: list[ChatMessage]


class ProjectCreate(BaseModel):
    """Request model for creating a project."""

    project_name: str = Field(min_length=1, max_length=255)
    project_description: str | None = Field(default=None, max_length=1000)

    @field_validator("project_name")
    @classmethod
    def strip_project_name(cls, value: str) -> str:
        """Reject blank names and strip surrounding whitespace."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Project name cannot be empty or whitespace only")
        return stripped


class ProjectUpdate(BaseModel):
    """Request model for updating a project."""

    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    project_description: str | None = Field(default=None, max_length=1000)

    @field_validator("project_name")
    @classmethod
    def strip_project_name(cls, value: str | None) -> str | None:
        """Reject blank names and strip surrounding whitespace."""
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Project name cannot be empty or whitespace only")
        return stripped


class Project(BaseModel):
    """Response model for a single project."""

    project_id: str
    project_name: str
    project_description: str | None = None
    username: str
    created_at: str
    updated_at: str
    thread_count: int = 0


class ProjectListResponse(BaseModel):
    """Response model for listing projects."""

    projects: list[Project]


class ProjectDeletionResponse(BaseModel):
    """Response model for project deletion."""

    status: str
    message: str
    project_id: str
    deleted_thread_ids: list[str] = []


class ProjectAssignRequest(BaseModel):
    """Request model for assigning a thread to a project."""

    thread_id: str
    project_id: str | None = None


class ProjectUnassignAllResponse(BaseModel):
    """Response model for unassigning all threads from a project."""

    status: str
    message: str
    project_id: str
    threads_unassigned: int
    unassigned_thread_ids: list[str] = []
