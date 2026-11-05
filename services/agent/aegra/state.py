"""LangGraph state schema for the aegra deployment.

Dormant: nothing imports it. The graph aegra builds carries its
state through `deepagents`' own schema, so this is the shape a
hand-rolled graph would use instead. Kept because it is the only
written record of that shape — deleting it would leave the
alternative undescribed rather than merely unused.
"""

from typing import Any, TypedDict

from agent.aegra import __version__


class AegraMetadata(TypedDict, total=False):
    """Platform-level metadata tracked alongside agent state."""

    run_id: str
    trace_id: str
    thread_id: str
    session_id: str
    user_id: str
    stream_tokens: bool
    error_count: int
    last_error: str | None


class HealthStatus(TypedDict):
    """Health check response schema."""

    status: str
    version: str
    agent_name: str
    model: str
    mcp_tools_loaded: int
    subagents_loaded: int
    backend_ready: bool


def make_health_status(
    *,
    agent_name: str,
    model: str,
    mcp_tools_count: int,
    subagents_count: int,
    backend_ready: bool,
) -> HealthStatus:
    """Build a health status dict from agent configuration."""
    return HealthStatus(
        status="healthy",
        version=__version__,
        agent_name=agent_name,
        model=model,
        mcp_tools_loaded=mcp_tools_count,
        subagents_loaded=subagents_count,
        backend_ready=backend_ready,
    )


def serialize_metadata(metadata: AegraMetadata) -> dict[str, Any]:
    """Serialize metadata to JSON-safe dict, dropping None values."""
    return {k: v for k, v in metadata.items() if v is not None}
