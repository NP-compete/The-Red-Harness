"""Put the agent's own description in front of the model."""

from __future__ import annotations

import time
from typing import Any

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_CACHE_SECONDS = settings.SELF_KNOWLEDGE_CACHE_SECONDS


def build_self_knowledge_middleware(
    user_id: str | None = None, model_name: str = ""
) -> Any:
    """Middleware describing the agent to itself, or None if there is nothing to say."""
    from agent.src.self_knowledge.describe import build_self_description

    try:
        from langchain.agents.middleware.types import AgentMiddleware
        from langchain_core.messages import SystemMessage
    except ImportError:
        logger.warning("AgentMiddleware unavailable — self-knowledge disabled")
        return None

    cache: dict[str, tuple[float, str, tuple[str, ...]]] = {}

    def _notice(connected: list[str], unconnected: list[str]) -> str:
        return build_self_description(model_name, connected, unconnected)

    static_notice = _notice([], [])

    class SelfKnowledgeMiddleware(AgentMiddleware):
        """Tell the model what it is, what it can reach, and what is refused."""

        async def awrap_model_call(self, request: Any, handler: Any) -> Any:
            notice = await self._notice()
            response = await handler(_apply(request, notice, SystemMessage))
            return _offer_connect(response, self._unconnected(), _asked_for(request))

        def wrap_model_call(self, request: Any, handler: Any) -> Any:
            hit = cache.get(user_id or "")
            response = handler(
                _apply(request, hit[1] if hit else static_notice, SystemMessage)
            )
            return _offer_connect(response, self._unconnected(), _asked_for(request))

        @staticmethod
        def _unconnected() -> tuple[str, ...]:
            hit = cache.get(user_id or "")
            return hit[2] if hit and len(hit) > 2 else ()

        async def _notice(self) -> str:
            key = user_id or ""
            hit = cache.get(key)
            now = time.monotonic()
            if hit and now - hit[0] < _CACHE_SECONDS:
                return hit[1]

            connected: list[str] = []
            unconnected: list[str] = []
            if user_id:
                try:
                    from agent.src.mcp_status.middleware import connection_state

                    connected, unconnected = await connection_state(user_id)
                except Exception:
                    logger.debug("Could not read MCP connection state", exc_info=True)

            notice = _notice(connected, unconnected)
            cache[key] = (now, notice, tuple(unconnected))
            return notice

    if not static_notice:
        logger.info("Self-knowledge: nothing to announce")
        return None

    logger.info("Self-knowledge active for user=%s model=%s", user_id, model_name)
    return SelfKnowledgeMiddleware()


def _asked_for(request: Any) -> str:
    """The user's own words for this turn, lowercased."""
    try:
        messages = list(getattr(request, "messages", None) or [])
    except Exception:
        return ""
    for message in reversed(messages):
        if getattr(message, "type", "") != "human":
            continue
        text = getattr(message, "text", "") or ""
        return text.lower() if isinstance(text, str) else ""
    return ""


def _offer_connect(
    response: Any, unconnected: tuple[str, ...], asked_for: str = ""
) -> Any:
    """Put a Connect button on a reply that declined for authorization."""
    if not unconnected:
        return response
    try:
        from agent.aegra.mcp_tool_auth import narrow_auth_requests

        message: Any = getattr(response, "result", None)
        if isinstance(message, list):
            message = message[0] if message else None
        if message is None:
            return response

        text = getattr(message, "text", "") or ""
        if not isinstance(text, str) or not text:
            return response
        haystack = text.lower()

        named = [
            n for n in unconnected if n.lower() in haystack and n.lower() in asked_for
        ]
        if not named:
            return response

        extra = getattr(message, "additional_kwargs", None)
        if not isinstance(extra, dict):
            extra = {}
            message.additional_kwargs = extra

        existing = extra.get("auth_required")
        requests = list(existing) if isinstance(existing, list) else []
        already = {r.get("mcp_name") for r in requests if isinstance(r, dict)}
        for name in named:
            if name in already:
                continue
            requests.append({"mcp_name": name, "reason": "not_connected"})

        requests = narrow_auth_requests(requests, text)
        extra["auth_required"] = requests
        if requests:
            logger.info(
                "Offering connect action for %s",
                ", ".join(str(r.get("mcp_name")) for r in requests),
            )
    except Exception:
        logger.warning("Could not offer connect action", exc_info=True)
    return response


def _apply(request: Any, notice: str, system_message_cls: Any) -> Any:
    """Append the notice to the request's system message."""
    if not notice:
        return request
    try:
        existing = getattr(request, "system_message", None)
        if existing is None:
            updated = system_message_cls(content=notice)
        elif isinstance(getattr(existing, "content", None), str):
            updated = existing.model_copy(
                update={"content": f"{existing.content}\n\n{notice}".strip()}
            )
        else:
            blocks = list(existing.content or [])
            blocks.append({"type": "text", "text": notice})
            updated = existing.model_copy(update={"content": blocks})
        return request.override(system_message=updated)
    except Exception:
        logger.debug("Could not attach the self-knowledge notice", exc_info=True)
        return request
