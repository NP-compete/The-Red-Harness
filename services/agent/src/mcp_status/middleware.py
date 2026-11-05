"""Tell the model which MCP servers it can actually reach."""

from __future__ import annotations

from typing import Any

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_CACHE_SECONDS = settings.MCP_STATUS_CACHE_SECONDS


def build_notice(connected: list[str], unconnected: list[str]) -> str:
    """The note describing which integrations are usable."""
    lines: list[str] = []
    if connected:
        lines.append("Connected and usable: " + ", ".join(sorted(connected)) + ".")
    if unconnected:
        lines.append(
            "Not connected, so their tools will fail: "
            + ", ".join(sorted(unconnected))
            + ". If one of these is needed, tell the user to connect it in "
            f"{settings.MCP_SETTINGS_PATH} rather than calling it and "
            "reporting the error."
        )
    return "\n".join(lines)


async def connection_state(user_id: str) -> tuple[list[str], list[str]]:
    """`(connected, unconnected)` server names for *user_id*."""
    try:
        from agent.aegra.mcp_oauth_handlers import handle_mcp_connections

        result = await handle_mcp_connections(user_id)
        entries = (result or {}).get("connections") or []
    except Exception:
        logger.debug("Could not read MCP connection state", exc_info=True)
        return [], []

    connected = [
        f"{e['mcp_name']} (as {e['account']})" if e.get("account") else e["mcp_name"]
        for e in entries
        if e.get("connected")
    ]
    unconnected = [e["mcp_name"] for e in entries if not e.get("connected")]
    return connected, unconnected


_PRIME_TASKS: set[Any] = set()


def build_mcp_status_middleware(user_id: str | None = None) -> Any:
    """Middleware announcing which MCP servers are connected."""
    import asyncio
    import time

    from langchain.agents.middleware.types import AgentMiddleware
    from langchain_core.messages import SystemMessage

    cache: dict[str, tuple[float, str, tuple[str, ...]]] = {}

    async def _prime() -> None:
        """Fill the cache before the first model call needs it."""
        if not user_id:
            return
        try:
            connected, unconnected = await connection_state(user_id)
            if connected or unconnected:
                cache[user_id] = (
                    time.monotonic(),
                    build_notice(connected, unconnected),
                    tuple(unconnected),
                )
        except Exception:
            logger.debug("Could not prime MCP status", exc_info=True)

    try:
        _task = asyncio.get_running_loop().create_task(_prime())
        _PRIME_TASKS.add(_task)
        _task.add_done_callback(_PRIME_TASKS.discard)
    except RuntimeError:
        pass

    class McpStatusMiddleware(AgentMiddleware):
        """Name the integrations the model can and cannot use."""

        async def awrap_model_call(self, request: Any, handler: Any) -> Any:
            notice = await self._notice(request)
            response = await handler(self._apply(request, notice))
            return self._offer_connect(response, self._unconnected(request))

        def wrap_model_call(self, request: Any, handler: Any) -> Any:
            user_id = self._user_id(request)
            cached = cache.get(user_id)
            notice = cached[1] if cached else ""
            response = handler(self._apply(request, notice))
            return self._offer_connect(response, self._unconnected(request))

        def _unconnected(self, request: Any) -> tuple[str, ...]:
            hit = cache.get(self._user_id(request))
            return hit[2] if hit and len(hit) > 2 else ()

        @staticmethod
        def _offer_connect(response: Any, unconnected: tuple[str, ...]) -> Any:
            """Put a Connect button on a reply that declined for auth."""
            if not unconnected:
                return response
            try:
                message: Any = getattr(response, "result", None)
                if isinstance(message, list):
                    message = message[0] if message else None
                if message is None:
                    return response

                text = getattr(message, "text", "") or ""
                if not isinstance(text, str) or not text:
                    return response
                haystack = text.lower()

                named = [n for n in unconnected if n.lower() in haystack]
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

                from agent.aegra.mcp_tool_auth import narrow_auth_requests

                requests = narrow_auth_requests(requests, text)
                if requests:
                    extra["auth_required"] = requests
            except Exception:
                logger.debug("Could not offer connect action", exc_info=True)
            return response

        @staticmethod
        def _user_id(request: Any) -> str:
            if user_id:
                return str(user_id)

            from agent.utils.pylogger import _user_id_var

            from_context = _user_id_var.get()
            if from_context:
                return str(from_context)

            state = getattr(request, "state", None)
            if isinstance(state, dict) and state.get("user_id"):
                return str(state["user_id"])
            return ""

        async def _notice(self, request: Any) -> str:
            user_id = self._user_id(request)
            if not user_id:
                return ""
            hit = cache.get(user_id)
            now = time.monotonic()
            if hit and now - hit[0] < _CACHE_SECONDS:
                return hit[1]

            connected, unconnected = await connection_state(user_id)
            notice = (
                build_notice(connected, unconnected)
                if (connected or unconnected)
                else ""
            )
            cache[user_id] = (now, notice, tuple(unconnected))
            return notice

        @staticmethod
        def _apply(request: Any, notice: str) -> Any:
            if not notice:
                return request
            existing = getattr(request, "system_message", None)
            try:
                if existing is None:
                    updated = SystemMessage(content=notice)
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
                logger.debug("Could not attach MCP status notice", exc_info=True)
                return request

    return McpStatusMiddleware()
