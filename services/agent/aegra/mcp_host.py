"""Request-scoped MCP Apps host proxy (resources + app tools/call)."""

from __future__ import annotations

import asyncio
import contextvars
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from types import SimpleNamespace
from typing import Any, cast

from fastapi import HTTPException
from langchain_mcp_adapters.client import MultiServerMCPClient

from agent.aegra.mcp import (
    _build_server_config,
    _get_mcp_breaker,
    _get_server_configs,
    _is_connection_error,
    _resolve_connection_token,
)
from agent.aegra.mcp_apps import (
    ensure_mcp_apps_capability_advertised,
    get_tool_visibility,
    is_app_callable,
)
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_MAX_TOOLS_LIST_PAGES = settings.MCP_TOOLS_LIST_MAX_PAGES


def _tool_from_mcp_meta(name: str, meta: dict[str, Any] | None) -> SimpleNamespace:
    """Adapt an MCP tool meta dict into the shape used by mcp_apps helpers."""
    return SimpleNamespace(name=name, metadata={"_meta": meta or {}})


def _authorization_required(mcp_name: str) -> HTTPException:
    from agent.aegra.mcp_auth import get_mcp_credential_resolver

    return HTTPException(
        status_code=401,
        detail={
            "error": "authorization_required",
            "mcp_name": mcp_name,
            "connect_url": get_mcp_credential_resolver().connect_url(mcp_name),
        },
    )


def _get_enabled_server(mcp_name: str) -> dict[str, Any]:
    entry = _get_server_configs().get(mcp_name)
    if not entry or not entry.get("enabled", False):
        raise HTTPException(
            status_code=404,
            detail=f"Unknown or disabled MCP server: {mcp_name}",
        )
    return entry


async def _resolve_bearer(
    mcp_name: str,
    entry: dict[str, Any],
    *,
    user_id: str,
    sso_token: str | None,
) -> str | None:
    """Resolve a bearer token for this request or raise HTTP 401 when required."""
    from agent.aegra.mcp_auth import NeedsAuthorization

    auth_mode = entry.get("auth_mode", "sso")
    auth_required = entry.get("auth", True)

    try:
        bearer = await _resolve_connection_token(mcp_name, entry, sso_token, user_id)
    except NeedsAuthorization:
        logger.info(
            "[%s] NeedsAuthorization during host bearer resolution",
            mcp_name,
        )
        raise _authorization_required(mcp_name) from None

    if not auth_required:
        return bearer

    if auth_mode in ("oauth", "dcr") and not bearer:
        logger.info(
            "[%s] no %s bearer token in host proxy — authorization required",
            mcp_name,
            auth_mode,
        )
        raise _authorization_required(mcp_name)

    if auth_mode == "sso" and not bearer:
        logger.info(
            "[%s] missing SSO bearer token in host proxy",
            mcp_name,
        )
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization bearer token for SSO MCP access",
        )

    if auth_mode == "api_key" and not bearer:
        logger.info(
            "[%s] api_key not configured on agent — host proxy blocked",
            mcp_name,
        )
        raise HTTPException(
            status_code=500,
            detail=f"MCP '{mcp_name}' api_key is not configured on the agent",
        )

    return bearer


_open_sessions: contextvars.ContextVar[dict[tuple[str, str], Any] | None] = (
    contextvars.ContextVar("_mcp_host_sessions", default=None)
)


async def enter_mcp_session_scope() -> None:
    """Begin reusing MCP sessions for this turn."""
    if _open_sessions.get() is None:
        cache: dict[tuple[str, str], Any] = {}
        _open_sessions.set(cache)
        await _evict_old_session_stacks()
        _session_stacks[id(cache)] = AsyncExitStack()


@asynccontextmanager
async def mcp_session_scope() -> AsyncIterator[None]:
    """Reuse MCP sessions for the duration of one turn."""
    stack = AsyncExitStack()
    token = _open_sessions.set({})
    try:
        async with stack:
            _session_stacks[id(_open_sessions.get())] = stack
            yield
    finally:
        _session_stacks.pop(id(_open_sessions.get() or {}), None)
        _open_sessions.reset(token)


_session_stacks: dict[int, AsyncExitStack] = {}

_MAX_SESSION_STACKS = 32


async def _evict_old_session_stacks() -> None:
    """Close the oldest stacks once there are more than the cap."""
    while len(_session_stacks) >= _MAX_SESSION_STACKS:
        _, stack = next(iter(_session_stacks.items()))
        _session_stacks.pop(next(iter(_session_stacks)), None)
        try:
            await stack.aclose()
        except Exception:
            logger.debug("Could not close an expired MCP session stack", exc_info=True)


@asynccontextmanager
async def mcp_session(
    mcp_name: str,
    *,
    user_id: str,
    sso_token: str | None,
) -> AsyncIterator[Any]:
    """Open an MCP client session, reusing one inside a session scope."""
    ensure_mcp_apps_capability_advertised()

    cache = _open_sessions.get()
    key = (mcp_name, user_id or "")
    if cache is not None and key in cache:
        yield cache[key]
        return

    entry = _get_enabled_server(mcp_name)
    bearer = await _resolve_bearer(
        mcp_name, entry, user_id=user_id, sso_token=sso_token
    )
    config = _build_server_config(entry, bearer)
    client = MultiServerMCPClient(cast("Any", {mcp_name: config}))
    timeout = float(entry.get("timeout", 30))

    if cache is not None:
        stack = _session_stacks.get(id(cache))
        if stack is not None:
            async with asyncio.timeout(timeout):
                session = await stack.enter_async_context(client.session(mcp_name))
            cache[key] = session
            logger.debug("[%s] MCP session opened for this turn", mcp_name)
            yield session
            return

    breaker = _get_mcp_breaker(mcp_name)
    if breaker.is_open:
        raise HTTPException(
            status_code=503,
            detail=(
                f"'{mcp_name}' is not answering and has been taken out of "
                "service for a minute. Nothing was sent to it."
            ),
        )

    async with AsyncExitStack() as opened:
        try:
            async with asyncio.timeout(timeout):
                session = await opened.enter_async_context(client.session(mcp_name))
        except TimeoutError:
            breaker.record_failure()
            logger.error(
                "[%s] host proxy MCP session timed out after %.0fs",
                mcp_name,
                timeout,
            )
            raise
        except Exception as failed:
            if _is_connection_error(failed):
                breaker.record_failure()
            logger.error(
                "[%s] host proxy MCP session failed",
                mcp_name,
                exc_info=True,
            )
            raise
        breaker.record_success()
        yield session


async def _find_mcp_tool(session: Any, tool_name: str) -> Any | None:
    """Find a tool by name using paginated tools/list (live server, not cache)."""
    cursor: str | None = None
    for _ in range(_MAX_TOOLS_LIST_PAGES):
        page = await session.list_tools(cursor=cursor)
        for tool in page.tools or []:
            if tool.name == tool_name:
                return tool
        cursor = page.nextCursor
        if not cursor:
            return None
    return None


async def list_tools(
    mcp_name: str,
    *,
    cursor: str | None = None,
    user_id: str,
    sso_token: str | None,
) -> dict[str, Any]:
    """Proxy ``tools/list`` on *mcp_name* (host metadata; live server)."""
    async with mcp_session(mcp_name, user_id=user_id, sso_token=sso_token) as session:
        result = await session.list_tools(cursor=cursor)

    payload = cast(
        dict[str, Any],
        result.model_dump(by_alias=True, mode="json", exclude_none=True),
    )
    logger.info(
        "MCP Apps tools/list ok server=%s count=%d",
        mcp_name,
        len(payload.get("tools") or []),
    )
    return payload


async def count_capabilities(
    mcp_name: str, *, user_id: str, sso_token: str | None
) -> dict[str, int | None]:
    """How many tools, resources and prompts *mcp_name* exposes."""
    counts: dict[str, int | None] = {"tools": None, "resources": None, "prompts": None}

    async with mcp_session(mcp_name, user_id=user_id, sso_token=sso_token) as session:
        for key, method in (
            ("tools", "list_tools"),
            ("resources", "list_resources"),
            ("prompts", "list_prompts"),
        ):
            call = getattr(session, method, None)
            if call is None:
                continue
            try:
                result = await call()
            except Exception as exc:
                logger.debug("MCP %s %s failed on %s: %s", mcp_name, method, key, exc)
                continue
            items = getattr(result, key, None)
            if items is not None:
                counts[key] = len(items)

    logger.info("MCP capabilities server=%s %s", mcp_name, counts)
    return counts


async def inventory(
    mcp_name: str, *, user_id: str, sso_token: str | None
) -> dict[str, list[dict[str, str]]]:
    """Name and description for every tool, resource and prompt."""
    out: dict[str, list[dict[str, str]]] = {
        "tools": [],
        "resources": [],
        "prompts": [],
    }

    async with mcp_session(mcp_name, user_id=user_id, sso_token=sso_token) as session:
        for key, method in (
            ("tools", "list_tools"),
            ("resources", "list_resources"),
            ("prompts", "list_prompts"),
        ):
            call = getattr(session, method, None)
            if call is None:
                continue
            try:
                result = await call()
            except Exception as exc:
                logger.debug("MCP %s %s failed: %s", mcp_name, method, exc)
                continue
            for item in getattr(result, key, None) or []:
                uri = str(getattr(item, "uri", "") or "")
                label = str(
                    getattr(item, "title", "") or getattr(item, "name", "") or uri
                )
                if not label:
                    continue
                description = str(getattr(item, "description", "") or "")
                entry: dict[str, Any] = {
                    "name": label,
                    "description": description[:300],
                }
                if uri and uri != label:
                    entry["uri"] = uri

                annotations = getattr(item, "annotations", None)
                if annotations is not None:
                    read_only = getattr(annotations, "readOnlyHint", None)
                    destructive = getattr(annotations, "destructiveHint", None)
                    if read_only is not None:
                        entry["read_only"] = bool(read_only)
                    if destructive is not None:
                        entry["destructive"] = bool(destructive)

                out[key].append(entry)

        for key, items in out.items():
            seen: dict[str, int] = {}
            for entry in items:
                seen[entry["name"]] = seen.get(entry["name"], 0) + 1
            for entry in items:
                if seen[entry["name"]] > 1 and entry.get("uri"):
                    entry["name"] = entry["uri"]
                    entry.pop("uri", None)

    logger.info(
        "MCP inventory server=%s tools=%d resources=%d prompts=%d",
        mcp_name,
        len(out["tools"]),
        len(out["resources"]),
        len(out["prompts"]),
    )
    return out


async def list_resources(
    mcp_name: str,
    *,
    cursor: str | None = None,
    user_id: str,
    sso_token: str | None,
) -> dict[str, Any]:
    """Proxy ``resources/list`` on *mcp_name* (View → Host → Server)."""
    async with mcp_session(mcp_name, user_id=user_id, sso_token=sso_token) as session:
        result = await session.list_resources(cursor=cursor)

    payload = cast(
        dict[str, Any],
        result.model_dump(by_alias=True, mode="json", exclude_none=True),
    )
    logger.info(
        "MCP Apps resources/list ok server=%s count=%d",
        mcp_name,
        len(payload.get("resources") or []),
    )
    return payload


async def list_resource_templates(
    mcp_name: str,
    *,
    cursor: str | None = None,
    user_id: str,
    sso_token: str | None,
) -> dict[str, Any]:
    """Proxy ``resources/templates/list`` on *mcp_name* (View → Host → Server)."""
    async with mcp_session(mcp_name, user_id=user_id, sso_token=sso_token) as session:
        result = await session.list_resource_templates(cursor=cursor)

    payload = cast(
        dict[str, Any],
        result.model_dump(by_alias=True, mode="json", exclude_none=True),
    )
    logger.info(
        "MCP Apps resources/templates/list ok server=%s count=%d",
        mcp_name,
        len(
            payload.get("resourceTemplates") or payload.get("resource_templates") or []
        ),
    )
    return payload


async def read_resource(
    mcp_name: str,
    uri: str,
    *,
    user_id: str,
    sso_token: str | None,
) -> dict[str, Any]:
    """Proxy ``resources/read`` for any resource URI on *mcp_name*."""
    if not isinstance(uri, str) or not uri.strip():
        raise HTTPException(status_code=400, detail="uri is required")

    async with mcp_session(mcp_name, user_id=user_id, sso_token=sso_token) as session:
        result = await session.read_resource(uri)

    payload = cast(
        dict[str, Any],
        result.model_dump(by_alias=True, mode="json", exclude_none=True),
    )
    logger.info(
        "MCP Apps resources/read ok server=%s uri=%s contents=%d",
        mcp_name,
        uri,
        len(payload.get("contents") or []),
    )
    return payload


read_ui_resource = read_resource


async def call_app_tool(
    mcp_name: str,
    tool_name: str,
    arguments: dict[str, Any] | None,
    *,
    user_id: str,
    sso_token: str | None,
) -> dict[str, Any]:
    """Proxy ``tools/call`` for an app-visible tool on *mcp_name*."""
    if not tool_name or not isinstance(tool_name, str):
        raise HTTPException(status_code=400, detail="tool name is required")

    not_found_detail: str | None = None
    deny_detail: dict[str, Any] | None = None
    result: Any | None = None

    async with mcp_session(mcp_name, user_id=user_id, sso_token=sso_token) as session:
        tool = await _find_mcp_tool(session, tool_name)
        if tool is None:
            not_found_detail = f"Tool not found on MCP server '{mcp_name}': {tool_name}"
        else:
            adapted = _tool_from_mcp_meta(tool.name, getattr(tool, "meta", None))
            if not is_app_callable(adapted):
                deny_detail = {
                    "error": "tool_not_app_callable",
                    "mcp_name": mcp_name,
                    "tool": tool_name,
                    "visibility": get_tool_visibility(adapted),
                }
            else:
                result = await session.call_tool(tool_name, arguments or {})

    if not_found_detail is not None:
        raise HTTPException(status_code=404, detail=not_found_detail)
    if deny_detail is not None:
        raise HTTPException(status_code=403, detail=deny_detail)
    if result is None:
        raise HTTPException(status_code=500, detail="tools/call produced no result")

    payload = cast(
        dict[str, Any],
        result.model_dump(by_alias=True, mode="json", exclude_none=True),
    )
    logger.info(
        "MCP Apps tools/call ok server=%s tool=%s isError=%s",
        mcp_name,
        tool_name,
        payload.get("isError", False),
    )
    return payload
