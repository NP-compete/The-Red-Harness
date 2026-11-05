"""Turning a typed command into the request it stands for."""

from __future__ import annotations

import dataclasses
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware

from agent.src.agent.command_catalogue import expand
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def build_command_middleware() -> Any:
    """Middleware that expands a slash command on the newest message."""

    class CommandMiddleware(AgentMiddleware):
        """Expand a slash command on the newest message."""

        async def awrap_model_call(self, request: Any, handler: Any) -> Any:
            """Call the model with any slash command expanded."""
            return await handler(_expanded(request))

        def wrap_model_call(self, request: Any, handler: Any) -> Any:
            """Call the model with any slash command expanded."""
            return handler(_expanded(request))

    return CommandMiddleware()


def _expanded(request: Any) -> Any:
    """The request with a slash command on its last message expanded."""
    try:
        messages = list(getattr(request, "messages", None) or [])
        if not messages:
            return request

        latest = messages[-1]
        if getattr(latest, "type", None) != "human":
            return request

        content = getattr(latest, "content", "")
        if not isinstance(content, str) or not content.startswith("/"):
            return request

        rewritten = expand(content)
        if rewritten == content:
            return request

        messages[-1] = latest.model_copy(update={"content": rewritten})
        return _with_messages(request, messages)
    except Exception:
        logger.debug("Could not expand a command", exc_info=True)
        return request


def _with_messages(request: Any, messages: list[Any]) -> Any:
    """`request` with its messages replaced."""
    if dataclasses.is_dataclass(request) and not isinstance(request, type):
        return dataclasses.replace(request, messages=messages)
    try:
        return request.override(messages=messages)
    except AttributeError:
        request.messages = messages
        return request
