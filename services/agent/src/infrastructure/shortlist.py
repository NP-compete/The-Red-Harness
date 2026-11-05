"""Narrowing the tool list to what a turn could plausibly need."""

from __future__ import annotations

from fnmatch import fnmatch
from typing import Any, Iterable, Sequence

from langchain.agents.middleware import AgentMiddleware

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def _belongs_to_a_server(tool_name: str, known: Sequence[str]) -> bool:
    """Whether this tool came from one of the connected servers."""
    return any(tool_name.startswith(f"{name}_") for name in known)


def _declared(tool_name: str, servers: Sequence[str]) -> bool:
    """Whether this tool belongs to one of the declared servers."""
    return any(tool_name.startswith(f"{name}_") for name in servers)


def _always(tool_name: str, patterns: Iterable[str]) -> bool:
    """Whether `tool_name` matches any of `patterns`."""
    return any(fnmatch(tool_name, pattern) for pattern in patterns)


_told_about_embedding = False


def _warn_once_about_embedding() -> None:
    """Warn, once per process, that embedding shortlisting is not built."""
    global _told_about_embedding  # noqa: PLW0603
    if _told_about_embedding:
        return
    _told_about_embedding = True
    logger.warning(
        "Tool shortlisting is set to 'embedding', which is not built yet; "
        "narrowing to the declared servers instead. That is the fallback "
        "the embedding strategy uses when a provider call fails, so it is "
        "a degradation rather than a surprise — but it is not what was asked for."
    )


def shortlist(
    tools: Sequence[Any],
    config: Any,
    *,
    declared_servers: Sequence[str] = (),
    known_servers: Sequence[str] | None = None,
    keep: Sequence[str] = (),
) -> list[Any]:
    """The tools to send this turn, in the order they arrived."""
    strategy = getattr(config, "strategy", "none")
    if strategy == "none":
        return list(tools)
    if strategy == "embedding":
        _warn_once_about_embedding()

    protected = set(keep)
    patterns = list(getattr(config, "always_include", []) or [])
    known = list(known_servers if known_servers is not None else declared_servers)

    chosen: list[Any] = []
    for tool in tools:
        name = getattr(tool, "name", "")
        if (
            name in protected
            or _always(name, patterns)
            or not _belongs_to_a_server(name, known)
            or _declared(name, declared_servers)
        ):
            chosen.append(tool)

    ceiling = int(getattr(config, "max_tools", 0) or 0)
    if ceiling and len(chosen) > ceiling:
        must = [
            t
            for t in chosen
            if getattr(t, "name", "") in protected
            or _always(getattr(t, "name", ""), patterns)
        ]
        rest = [t for t in chosen if t not in must]
        chosen = must + rest[: max(0, ceiling - len(must))]

    return chosen


def _already_called(state: Any) -> set[str]:
    """Tools this run has already called."""
    messages = (state or {}).get("messages") if isinstance(state, dict) else None
    if not isinstance(messages, list):
        return set()

    used: set[str] = set()
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            name = call.get("name") if isinstance(call, dict) else None
            if isinstance(name, str) and name:
                used.add(name)
    return used


class ToolShortlistMiddleware(AgentMiddleware):
    """Narrows the tool list for one model call and no further."""

    def __init__(
        self,
        *,
        config: Any,
        declared_servers: Sequence[str] = (),
        known_servers: Sequence[str] | None = None,
    ) -> None:
        """Bind to `config` and the servers whose tools may be offered."""
        super().__init__()
        self._config = config
        self._declared = tuple(declared_servers)
        self._known = known_servers

    def _narrowed(self, request: Any) -> Any:
        """The request to pass on, narrowed when a strategy asks."""
        if getattr(self._config, "strategy", "none") == "none":
            return request

        chosen = shortlist(
            request.tools,
            self._config,
            declared_servers=self._declared,
            known_servers=self._known,
            keep=tuple(_already_called(getattr(request, "state", None))),
        )
        if len(chosen) == len(request.tools):
            return request

        logger.info(
            "Shortlisted %d of %d tools for this call",
            len(chosen),
            len(request.tools),
        )
        return request.override(tools=chosen)

    def wrap_model_call(self, request: Any, handler: Any) -> Any:
        """Call the model with the tool list narrowed."""
        return handler(self._narrowed(request))

    async def awrap_model_call(self, request: Any, handler: Any) -> Any:
        """Call the model with the tool list narrowed."""
        return await handler(self._narrowed(request))


def tool_prefixes(server_names: Sequence[str], servers: Any) -> list[str]:
    """What each server's tools are actually called."""
    found: list[str] = []
    for name in server_names:
        config = (servers or {}).get(name) if hasattr(servers, "get") else None
        declared = (config or {}).get("tool_prefix") if hasattr(config, "get") else None
        found.append(str(declared).strip() or name if declared else name)
    return found
