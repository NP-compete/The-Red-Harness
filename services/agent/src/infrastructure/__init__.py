"""Infrastructure layer for external system integrations."""

from .backend import get_backend, get_configured_backend
from .mcp import get_mcp_tools
from .subagents import load_subagents

__all__ = [
    "get_mcp_tools",
    "get_backend",
    "get_configured_backend",
    "load_subagents",
]
