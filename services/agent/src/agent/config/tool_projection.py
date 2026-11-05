"""What this agent publishes to a system calling it."""

from __future__ import annotations

from typing import Any

from agent.src.agent.config.inbound import PublishedTool

_ASK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "description": "What to ask this agent",
        },
        "thread_id": {
            "type": "string",
            "description": ("Continue an existing conversation. Omit to start one."),
        },
    },
    "required": ["question"],
    "additionalProperties": False,
}

SCHEMA_FOR: dict[str, dict[str, Any]] = {
    "read": _ASK_SCHEMA,
    "act": _ASK_SCHEMA,
}


def project_tools(declared: tuple[PublishedTool, ...]) -> list[dict[str, Any]]:
    """The published tool list, in the order it was declared."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": SCHEMA_FOR.get(tool.scope, _ASK_SCHEMA),
        }
        for tool in declared
    ]


def scope_of(name: str, declared: tuple[PublishedTool, ...]) -> str | None:
    """What a declared tool may do, or nothing if it was not declared."""
    for tool in declared:
        if tool.name == name:
            return tool.scope
    return None
