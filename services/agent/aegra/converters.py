"""State conversion utilities for Aegra integration.

Dormant: nothing imports it. It converts between this deployment's
state dicts and the LangGraph message shapes; the live path hands
those to the library already converted. Kept because the mapping it
encodes is not written down anywhere else.
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


def stream_request_to_langgraph_input(message: str) -> dict[str, Any]:
    """Convert a raw user message into LangGraph-compatible input."""
    return {"messages": [HumanMessage(content=message)]}


def langgraph_messages_to_dicts(messages: list) -> list[dict[str, Any]]:
    """Convert LangChain message objects to plain dicts for serialization."""
    result = []
    for msg in messages:
        entry: dict[str, Any] = {"content": msg.content}
        if isinstance(msg, HumanMessage):
            entry["role"] = "human"
        elif isinstance(msg, AIMessage):
            entry["role"] = "ai"
        elif isinstance(msg, SystemMessage):
            entry["role"] = "system"
        else:
            entry["role"] = "unknown"

        if hasattr(msg, "tool_calls") and msg.tool_calls:
            entry["tool_calls"] = [
                {"name": tc["name"], "args": tc["args"]} for tc in msg.tool_calls
            ]
        result.append(entry)
    return result


def extract_final_response(state: dict[str, Any]) -> str | None:
    """Extract the final AI response text from a LangGraph state snapshot."""
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and isinstance(msg.content, str) and msg.content:
            return msg.content
    return None
