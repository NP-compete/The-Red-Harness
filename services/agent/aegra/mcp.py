"""MCP (Model Context Protocol) client for external tool integration."""

import asyncio
import base64
import contextvars
import json
import math
import os
import time
from collections import OrderedDict
from typing import Any, cast

import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient

from agent.aegra.mcp_apps import (
    McpAppCallToolResultInterceptor,
    ensure_mcp_apps_capability_advertised,
    prepare_tools_for_model,
)
from agent.src.agent.config import agent_config
from agent.src.error_handling import CircuitBreaker, create_circuit_breaker
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger(log_level=settings.PYTHON_LOG_LEVEL)

ensure_mcp_apps_capability_advertised()

_SSO_TOKEN_URL: str = ""

_mcp_breakers: dict[str, CircuitBreaker] = {}

_background: set[Any] = set()


def _in_the_background(coro: Any) -> Any:
    """Run a coroutine without letting the garbage collector eat it."""
    task = asyncio.ensure_future(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)
    return task


_SHARED_BREAKER_KEY = settings.MCP_SHARED_BREAKER_KEY

_MCP_TOOL_CACHE_TTL: float = float(agent_config.get_cache_config().mcp.ttl)

_refreshing: set[str] = set()
_MCP_AUTH_SET_TTL = settings.MCP_AUTH_SET_TTL_SECONDS

_MCP_TOOL_CACHE_MAX_USERS: int = int(os.environ.get("MCP_TOOL_CACHE_MAX_USERS", "200"))
_cached_tools: OrderedDict[str | None, list[Any]] = OrderedDict()
_cached_tools_ts: dict[str | None, float] = {}
_cached_connected_set: dict[str | None, set[str]] = {}


def _forget_cached_tools(key: str | None) -> None:
    """Drop one cache entry from every structure that tracks it."""
    _cached_tools.pop(key, None)
    _cached_tools_ts.pop(key, None)
    _cached_connected_set.pop(key, None)
    if isinstance(key, str):
        _refreshing.discard(key)


def _touch_cached_tools(key: str | None) -> None:
    """Mark an entry as recently used."""
    if key in _cached_tools:
        _cached_tools.move_to_end(key)


def _store_cached_tools(key: str | None, tools: list[Any], connected: set[str]) -> None:
    """Record one user's tool list, evicting the least recently used."""
    _cached_tools[key] = tools
    _cached_tools.move_to_end(key)
    _cached_tools_ts[key] = time.time()
    _cached_connected_set[key] = connected

    while len(_cached_tools) > _MCP_TOOL_CACHE_MAX_USERS:
        oldest, _ = _cached_tools.popitem(last=False)
        _cached_tools_ts.pop(oldest, None)
        _cached_connected_set.pop(oldest, None)
        if isinstance(oldest, str):
            _refreshing.discard(oldest)
        logger.info(
            "MCP tool cache full (%d users) — evicted %s",
            _MCP_TOOL_CACHE_MAX_USERS,
            oldest,
        )


_current_access_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_access_token", default=None
)
_current_refresh_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_refresh_token", default=None
)
_current_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_user_id", default=None
)

_MAX_USER_TOKENS = 512
_user_token_cache: OrderedDict[str, tuple[str, str]] = OrderedDict()


def _remember_user_token(user_id: str, tokens: tuple[str, str]) -> None:
    """Keep this user's tokens, and let the oldest person's go."""
    _user_token_cache[user_id] = tokens
    _user_token_cache.move_to_end(user_id)
    while len(_user_token_cache) > _MAX_USER_TOKENS:
        _user_token_cache.popitem(last=False)


_mcp_tool_discovery: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_mcp_tool_discovery", default=False
)


def set_mcp_auth_context(
    access_token: str | None,
    refresh_token: str | None,
    user_id: str | None = None,
) -> None:
    """Store the current request's tokens for tool-call-time auth injection."""
    _current_access_token.set(access_token)
    _current_refresh_token.set(refresh_token)
    _current_user_id.set(user_id)


class _TokenInjectorInterceptor:
    """Inject the correct per-MCP bearer token into every MCP tool call."""

    def __init__(
        self,
        mcp_name: str,
        server_cfg: dict[str, Any],
        server_key: str | None = None,
    ) -> None:
        self._mcp_name = mcp_name
        self._server_cfg = server_cfg
        self._server_key = server_key or mcp_name

    async def __call__(self, request: Any, handler: Any) -> Any:
        from agent.aegra.mcp_auth import (
            NeedsAuthorization,
            get_mcp_credential_resolver,
        )

        user_id = _current_user_id.get()
        auth_mode = self._server_cfg.get("auth_mode", "sso")

        if auth_mode == "api_key":
            return await handler(request)

        try:
            if auth_mode in ("oauth", "dcr"):
                if not user_id:
                    if _mcp_tool_discovery.get():
                        logger.info(
                            "[%s] no user_id during %s tool discovery — proceeding unauthenticated",
                            self._mcp_name,
                            auth_mode,
                        )
                        access = None
                    else:
                        raise NeedsAuthorization(
                            self._server_key,
                            get_mcp_credential_resolver().connect_url(self._server_key),
                        )
                else:
                    try:
                        access = await get_mcp_credential_resolver().resolve(
                            user_id, self._server_key, self._server_cfg
                        )
                    except NeedsAuthorization:
                        if _mcp_tool_discovery.get():
                            logger.info(
                                "[%s] NeedsAuthorization during %s tool discovery "
                                "— proceeding unauthenticated (will create placeholder)",
                                self._mcp_name,
                                auth_mode,
                            )
                            access = None
                        else:
                            raise
            else:
                access = _current_access_token.get()
                if access:
                    access = await refresh_access_token(
                        access, _current_refresh_token.get()
                    )
        except NeedsAuthorization:
            raise
        except Exception as exc:
            logger.error(
                "[%s] credential resolution failed", self._mcp_name, exc_info=True
            )
            if auth_mode == "sso":
                access = _current_access_token.get()
            else:
                raise RuntimeError(
                    f"[{self._mcp_name}] {auth_mode} credential resolution failed"
                ) from exc

        if access:
            request = request.override(headers={"Authorization": f"Bearer {access}"})
        elif self._server_cfg.get("auth", True):
            logger.warning(
                "TokenInjector: no token for MCP '%s' — call may fail auth",
                self._mcp_name,
            )
        return await handler(request)


def _get_mcp_breaker(server_name: str | None = None) -> CircuitBreaker:
    """Lazy-init a circuit breaker for one MCP server."""
    key = server_name or _SHARED_BREAKER_KEY
    breaker = _mcp_breakers.get(key)
    if breaker is None:
        breaker = create_circuit_breaker(
            f"mcp-server:{key}", threshold=5, reset_timeout=60.0
        )
        _mcp_breakers[key] = breaker
    return breaker


def _get_token_endpoint() -> str:
    """Derive the OIDC token endpoint from SSO_ISSUER_URL (cached)."""
    global _SSO_TOKEN_URL  # noqa: PLW0603
    if _SSO_TOKEN_URL:
        return _SSO_TOKEN_URL
    issuer: str = os.environ.get("SSO_ISSUER_URL", "").rstrip("/")
    if issuer:
        _SSO_TOKEN_URL = f"{issuer}/protocol/openid-connect/token"
    return _SSO_TOKEN_URL


def _jwt_exp(token: str) -> float:
    """Extract ``exp`` from a JWT payload without cryptographic validation."""
    try:
        payload: str = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        data: dict[str, Any] = json.loads(base64.urlsafe_b64decode(payload))
        return float(data.get("exp", 0))
    except Exception:
        return 0.0


def _jwt_exp_or_none(token: str) -> float | None:
    """``exp`` from a JWT, or ``None`` when there is no readable claim."""
    try:
        payload: str = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        data: dict[str, Any] = json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None
    exp = data.get("exp")
    return float(exp) if exp is not None else None


def _token_remaining(token: str) -> float:
    """Seconds of life left in a token, or ``inf`` if it has no readable exp."""
    exp = _jwt_exp(token)
    if exp == 0.0 and _jwt_exp_or_none(token) is None:
        return math.inf
    return exp - time.time()


_SSO_REFRESH_BUFFER_SECS = settings.MCP_SSO_REFRESH_BUFFER_SECONDS

_sso_refresh_lock: asyncio.Lock = asyncio.Lock()


async def refresh_access_token(
    access_token: str,
    refresh_token: str | None,
    user_id: str | None = None,
) -> str:
    """Return a fresh access token, using the refresh_token grant if needed."""
    remaining: float = _token_remaining(access_token)
    if remaining > _SSO_REFRESH_BUFFER_SECS:
        logger.debug("Access token still valid (%.0fs remaining)", remaining)
        return access_token

    if not refresh_token:
        logger.warning(
            "Access token near expiry (%.0fs) but no refresh_token available", remaining
        )
        return access_token

    token_url: str = _get_token_endpoint()
    client_id: str = os.environ.get("SSO_CLIENT_ID", "")
    client_secret: str = os.environ.get("SSO_CLIENT_SECRET", "")  # noqa: F841
    if not token_url or not client_id:
        logger.warning("Cannot refresh token — SSO_ISSUER_URL or SSO_CLIENT_ID not set")
        return access_token

    resolved_user_id = user_id or _current_user_id.get() or "unknown"
    return await _locked_sso_refresh(
        access_token, refresh_token, remaining, resolved_user_id
    )


async def _locked_sso_refresh(
    access_token: str,
    refresh_token: str,
    remaining: float,
    user_id: str = "unknown",
) -> str:
    """Perform the actual SSO refresh under a lock to prevent concurrent races."""
    from agent.aegra.redis import distributed_lock

    lock_name = f"sso:refresh:{user_id}"

    async with distributed_lock(lock_name, ttl_seconds=15, wait_seconds=10) as state:
        cached = _user_token_cache.get(user_id)
        if state == "no_redis":
            async with _sso_refresh_lock:
                cached = _user_token_cache.get(user_id)
                if cached:
                    cached_at, cached_rt = cached
                    if cached_at != access_token:
                        check_remaining = _token_remaining(cached_at)
                        if check_remaining > _SSO_REFRESH_BUFFER_SECS:
                            logger.debug(
                                "SSO token already refreshed by peer (no-redis path)"
                            )
                            return cached_at
                latest_rt = (cached[1] if cached else None) or refresh_token
                return await _do_sso_refresh(access_token, latest_rt, remaining)
        elif state == "timeout":
            if cached:
                cached_at, _ = cached
                if cached_at != access_token:
                    check_remaining = _token_remaining(cached_at)
                    if check_remaining > _SSO_REFRESH_BUFFER_SECS:
                        logger.info(
                            "SSO refresh lock timeout — another task refreshed (%.0fs left)",
                            check_remaining,
                        )
                        return cached_at
            logger.warning("SSO refresh lock timeout — using current token")
            return access_token
        else:
            cached = _user_token_cache.get(user_id)
            if cached:
                cached_at, cached_rt = cached
                if cached_at != access_token:
                    check_remaining = _token_remaining(cached_at)
                    if check_remaining > _SSO_REFRESH_BUFFER_SECS:
                        logger.debug("SSO token already refreshed by another task")
                        return cached_at
            latest_rt = (cached[1] if cached else None) or refresh_token
            return await _do_sso_refresh(access_token, latest_rt, remaining)


async def _do_sso_refresh(
    access_token: str,
    refresh_token: str,
    remaining: float,
) -> str:
    """Execute the OIDC refresh grant and update context vars."""
    logger.info("Refreshing SSO access token (%.0fs remaining)", remaining)
    try:
        from agent.aegra.auth import EVAL_TOKEN_REFRESH_ENABLED, _oidc_refresh

        new_token, new_rt = await _oidc_refresh(refresh_token)
        new_remaining: float = _token_remaining(new_token)
        logger.info("SSO token refreshed (%.0fs lifetime)", new_remaining)

        _current_access_token.set(new_token)
        if new_rt != refresh_token:
            _current_refresh_token.set(new_rt)
        sub = _current_user_id.get()
        if sub:
            _remember_user_token(sub, (new_token, new_rt))
            if EVAL_TOKEN_REFRESH_ENABLED:
                from agent.aegra.mcp_crypto import encrypt_secret
                from agent.aegra.redis import cache_get, cache_set, run_redis

                if await run_redis(cache_get, f"eval:active:{sub}"):
                    encrypted_rt = encrypt_secret(new_rt)
                    if encrypted_rt:
                        await run_redis(
                            cache_set, f"eval:refresh:{sub}", encrypted_rt, 3600
                        )

        return new_token
    except Exception:
        logger.error("Token refresh failed — using original token", exc_info=True)
        return access_token


def mcp_httpx_verify(server_cfg: dict[str, Any]) -> bool:
    """Return the httpx ``verify`` flag for an MCP server config (default True)."""
    from agent.src.settings import settings

    ssl_verify = bool(server_cfg.get("ssl_verify", True))

    if settings.is_production and not ssl_verify:
        server_name = server_cfg.get("name", "unknown")
        logger.error(
            "MCP server '%s' has ssl_verify=false, which is not permitted in production. "
            "SSL verification will be enforced.",
            server_name,
        )
        return True

    return ssl_verify


def _get_server_configs() -> dict[str, dict[str, Any]]:
    """Get pre-loaded MCP server configurations."""
    return agent_config.get_mcp_servers()


async def _resolve_connection_token(
    name: str,
    entry: dict[str, Any],
    sso_token: str | None,
    user_id: str | None,
) -> str | None:
    """Resolve the bearer token used for MCP connection/tool discovery."""
    auth_mode = entry.get("auth_mode", "sso")
    if auth_mode == "sso":
        return sso_token

    if auth_mode == "api_key":
        reference = entry.get("auth_env_var", "")
        from agent.src.security.secret_source import SecretUnavailable, resolve

        try:
            return resolve(str(reference)).strip().strip('"') or None
        except SecretUnavailable as missing:
            logger.warning("MCP auth_mode=api_key but %s", missing)
            return None

    if not user_id:
        return None

    from agent.aegra.mcp_auth import (
        NeedsAuthorization,
        get_mcp_credential_resolver,
    )

    try:
        return await get_mcp_credential_resolver().resolve(
            user_id,
            name,
            entry,
            renew_buffer_seconds=settings.MCP_TOKEN_RENEW_BUFFER_SECONDS,
        )
    except NeedsAuthorization as exc:
        logger.info(
            "[%s] no usable OAuth token during connection token resolution (%s)",
            name,
            exc.reason,
        )
        from agent.aegra.mcp_tool_auth import record_auth_request

        record_auth_request(exc)
        return None


def _bearer_refresher(
    name: str,
    entry: dict[str, Any],
    auth_mode: str,
    user_id: str | None,
) -> Any:
    """An async callable giving this server's current access token."""
    if auth_mode not in ("oauth", "dcr") or not user_id:
        return None

    async def _current() -> str | None:
        from agent.aegra.mcp_auth import get_mcp_credential_resolver

        return await get_mcp_credential_resolver().resolve(user_id, name, entry)

    return _current


class _FreshBearer(httpx.Auth):
    """Attach the access token per request, not per graph build."""

    def __init__(self, resolve: Any, fallback: str | None) -> None:
        self._resolve = resolve
        self._fallback = fallback

    async def async_auth_flow(self, request: httpx.Request) -> Any:
        token = self._fallback
        try:
            fresh = await self._resolve()
            if fresh:
                token = fresh
        except Exception:
            logger.debug("Could not refresh MCP bearer", exc_info=True)
        if token:
            request.headers["Authorization"] = f"Bearer {token}"
        yield request


def _build_server_config(
    entry: dict[str, Any],
    bearer_token: str | None,
    refresh_bearer: Any = None,
) -> dict[str, Any]:
    """Build MultiServerMCPClient config from server definition."""
    from agent.utils.pylogger import _trace_id_var

    authenticated = bool(entry.get("auth", True)) and bearer_token is not None
    headers: dict[str, str] = {}
    if authenticated:
        headers["Authorization"] = f"Bearer {bearer_token}"

    trace_id = _trace_id_var.get()
    if trace_id:
        headers["X-Trace-ID"] = trace_id

    config: dict[str, Any] = {
        "url": entry["url"],
        "transport": entry.get("transport", "streamable_http"),
        "headers": headers,
    }

    verify = mcp_httpx_verify(entry)
    if not verify:
        from agent.src.settings import settings

        if settings.is_production:
            logger.warning(
                "MCP server '%s': ssl_verify forced to True in production",
                entry.get("name", entry.get("url", "unknown")),
            )
            verify = True

    ours: httpx.Auth | None = (
        _FreshBearer(refresh_bearer, bearer_token)
        if authenticated and refresh_bearer is not None
        else None
    )

    if ours is not None or not verify:

        def _factory(
            auth: httpx.Auth | None = None,
            _ours: httpx.Auth | None = ours,
            _verify: bool = verify,
            **kw: Any,
        ) -> httpx.AsyncClient:
            return httpx.AsyncClient(  # nosec B501 - verify is forced True in prod
                verify=_verify,
                auth=auth or _ours,
                **kw,
            )

        config["httpx_client_factory"] = _factory

    return config


def _create_auth_placeholder_tool(
    mcp_name: str,
    server_cfg: dict[str, Any] | None = None,
    *,
    tools_present: bool = False,
) -> Any:
    """Create a stub tool standing in for a server that needs authorizing."""
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel
    from pydantic import Field as PydanticField

    class _Input(BaseModel):
        query: str = PydanticField(default="", description="Your request for this tool")

    safe = mcp_name.replace("-", "_")
    svc_desc = (server_cfg or {}).get("description", f"{mcp_name} services")

    async def _require_auth(query: str = "") -> str:
        from langgraph.errors import GraphBubbleUp as _GraphBubbleUp

        from agent.aegra.mcp_auth import (
            NeedsAuthorization,
            get_mcp_credential_resolver,
        )

        resolver = get_mcp_credential_resolver()
        user_id = _current_user_id.get()
        if not user_id:
            raise NeedsAuthorization(mcp_name, resolver.connect_url(mcp_name))

        cfg = _get_server_configs().get(mcp_name, {})

        async def _connected() -> bool:
            try:
                await resolver.resolve(user_id, mcp_name, cfg)
                return True
            except NeedsAuthorization:
                return False
            except _GraphBubbleUp:
                raise
            except Exception:
                logger.warning(
                    "[%s] placeholder tool auth resolve failed "
                    "— treating as not connected",
                    mcp_name,
                    exc_info=True,
                )
                return False

        if not await _connected():
            raise NeedsAuthorization(mcp_name, resolver.connect_url(mcp_name))

        if tools_present:
            return (
                f"{mcp_name} is connected and its tools are "
                f"available in this turn. Call them directly."
            )

        invalidate_mcp_tool_cache(user_id)
        return (
            f"[TOOLS_RELOADED mcp={mcp_name}] {mcp_name} is now "
            f"available in this run. Call its tools directly and "
            f"answer the question. Do not ask the user for anything."
        )

    return StructuredTool(
        name=f"mcp__{safe}",
        description=(
            f"Access {svc_desc} — NOT CONNECTED. "
            f"Call this only when answering genuinely requires data from it. "
            f"Do not call it to check whether it is available, to list what "
            f"you can do, or to answer a question about your own capabilities. "
            f"It returns a notice that the server needs connecting, nothing more."
        ),
        func=lambda query="": "",
        coroutine=_require_auth,
        args_schema=_Input,
    )


def _apply_tool_allowlist(
    name: str,
    server_cfg: dict[str, Any],
    tools: list[Any],
) -> list[Any]:
    """Narrow a server's tool surface to the ``tools`` list in mcp.json."""
    allow = server_cfg.get("tools")
    if not allow:
        return tools
    allowed = set(allow)
    kept = [t for t in tools if t.name in allowed]
    missing = allowed - {t.name for t in tools}
    if missing:
        logger.error(
            "[%s] mcp.json allows %d tool(s) the server does not offer: %s",
            name,
            len(missing),
            sorted(missing),
        )
    if not kept:
        logger.error(
            "[%s] tool allowlist matched nothing — server contributes no tools",
            name,
        )
    else:
        logger.info(
            "[%s] tool allowlist kept %d of %d tool(s)", name, len(kept), len(tools)
        )
    return kept


async def _connect_single_server(
    name: str,
    config: dict[str, Any],
    server_cfg: dict[str, Any],
    timeout: int,
    *,
    required: bool = False,
    server_key: str | None = None,
    mcp_server: str | None = None,
) -> list[Any]:
    """Connect to one MCP server and return its model-visible tools."""
    auth_key = server_key or mcp_server or name
    breaker = _get_mcp_breaker(mcp_server or name)
    if breaker.is_open:
        logger.warning(f"[{name}] circuit breaker open — skipping connection")
        return []

    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            async with asyncio.timeout(timeout):
                client = MultiServerMCPClient(
                    cast("Any", {name: config}),
                    tool_interceptors=[
                        _TokenInjectorInterceptor(
                            name, server_cfg, server_key=auth_key
                        ),
                        McpAppCallToolResultInterceptor(),
                    ],
                    tool_name_prefix=bool(server_cfg.get("tool_prefix", "")),
                )
                tools: list[Any] = await client.get_tools()
            tools = _apply_tool_allowlist(name, server_cfg, tools)
            model_tools = prepare_tools_for_model(tools, auth_key)
            skipped = len(tools) - len(model_tools)
            if skipped:
                logger.info(
                    "[%s] hid %d app-only tool(s) from the model (%d model-visible)",
                    name,
                    skipped,
                    len(model_tools),
                )
            logger.info(f"[{name}] loaded {len(model_tools)} tool(s)")
            breaker.record_success()
            return model_tools
        except TimeoutError:
            if attempt < max_attempts:
                logger.warning(
                    f"[{name}] timeout after {timeout}s (attempt {attempt}/{max_attempts}), retrying"
                )
                continue
            breaker.record_failure()
            logger.error(f"[{name}] timeout after {timeout}s ({config.get('url')})")
        except Exception as exc:
            if _is_needs_authorization(exc):
                logger.info(
                    "[%s] MCP OAuth required — returning auth placeholder tool (%s: %s)",
                    name,
                    type(exc).__name__,
                    exc,
                )
                return prepare_tools_for_model(
                    [_create_auth_placeholder_tool(auth_key, server_cfg)],
                    auth_key,
                )
            elif _is_auth_error(exc):
                auth_mode = server_cfg.get("auth_mode", "sso")
                if auth_mode in ("oauth", "dcr"):
                    logger.info(
                        "[%s] MCP tool discovery auth failed (auth_mode=%s) "
                        "— returning auth placeholder tool (%s: %s)",
                        name,
                        auth_mode,
                        type(exc).__name__,
                        exc,
                    )
                    return prepare_tools_for_model(
                        [_create_auth_placeholder_tool(auth_key, server_cfg)],
                        auth_key,
                    )
                else:
                    logger.warning(
                        f"[{name}] MCP auth failed — {type(exc).__name__}: {exc}"
                    )
            elif _is_connection_error(exc) and not required:
                breaker.record_failure()
                logger.warning(
                    f"[{name}] not reachable ({config.get('url')}) — skipped"
                )
            else:
                breaker.record_failure()
                logger.error(
                    f"[{name}] connection failed ({config.get('url')})", exc_info=True
                )
            return []
    return []


def _is_needs_authorization(exc: BaseException) -> bool:
    """Check if an exception chain contains NeedsAuthorization."""
    from agent.aegra.mcp_auth import NeedsAuthorization

    for sub in getattr(exc, "exceptions", [exc]):
        if isinstance(sub, NeedsAuthorization):
            return True
        if (
            hasattr(sub, "__cause__")
            and sub.__cause__
            and _is_needs_authorization(sub.__cause__)
        ):
            return True
    return False


def _is_auth_error(exc: BaseException) -> bool:
    """Check if an exception is caused by an HTTP 401/403 response."""
    for sub in getattr(exc, "exceptions", [exc]):
        response = getattr(sub, "response", None)
        if response is not None:
            status = getattr(response, "status_code", None)
            if status in (401, 403):
                return True
        msg: str = str(sub)
        if "401" in msg or "403" in msg or "Unauthorized" in msg or "Forbidden" in msg:
            return True
        if sub.__cause__ and _is_auth_error(sub.__cause__):
            return True
        if (
            sub.__context__
            and sub is not sub.__context__
            and _is_auth_error(sub.__context__)
        ):
            return True
    return False


def _is_connection_error(exc: BaseException) -> bool:
    """Check if an exception is a connection refused / unreachable error."""
    for sub in getattr(exc, "exceptions", [exc]):
        if isinstance(sub, ConnectionError):
            return True
        msg: str = str(sub).lower()
        if (
            "connecterror" in msg
            or "connection attempts failed" in msg
            or "connection refused" in msg
        ):
            return True
        if hasattr(sub, "__cause__") and sub.__cause__:
            if _is_connection_error(sub.__cause__):
                return True
    return False


def _filter_by_names(
    enabled: dict[str, dict[str, Any]],
    server_names: list[str] | None,
) -> dict[str, dict[str, Any]]:
    """Restrict *enabled* servers to only those declared in *server_names*."""
    if not server_names:
        return enabled
    requested = set(server_names)
    missing = requested - set(enabled)
    if missing:
        logger.warning(
            "Declared MCP server(s) not found or not enabled: %s",
            ", ".join(sorted(missing)),
        )
    return {k: v for k, v in enabled.items() if k in requested}


def invalidate_mcp_tool_cache(user_id: str | None = None) -> None:
    """Clear the MCP tool cache."""
    if user_id is not None:
        prefix = f"{user_id}:"
        keys = [k for k in _cached_tools if k is not None and k.startswith(prefix)]
        for k in keys:
            _forget_cached_tools(k)
    else:
        _cached_tools.clear()
        _cached_tools_ts.clear()
        _cached_connected_set.clear()
        _refreshing.clear()


async def get_mcp_tools(
    sso_token: str | None = None,
    server_names: list[str] | None = None,
    user_id: str | None = None,
) -> list[Any]:
    """Connect to MCP server(s) and retrieve available tools."""
    server_key = ",".join(sorted(server_names)) if server_names else ""
    cache_key: str | None = f"{user_id}:{server_key}" if user_id else None
    cached = _cached_tools.get(cache_key) if cache_key else None
    cached_ts = _cached_tools_ts.get(cache_key, 0.0) if cache_key else 0.0

    from agent.aegra.redis import cache_expire, cache_smembers, run_redis

    auth_set_key = f"mcp_auth_set:{settings.agent_deployment_id}:{user_id}"

    if (
        cached
        and len(cached) > 0
        and (time.time() - cached_ts) >= _MCP_TOOL_CACHE_TTL
        and cache_key
        and cache_key not in _refreshing
    ):
        _refreshing.add(cache_key)
        revalidate_key: str = cache_key

        async def _revalidate(key: str = revalidate_key) -> None:
            try:
                await get_mcp_tools(
                    sso_token=sso_token, server_names=server_names, user_id=user_id
                )
            except Exception:
                logger.debug("Background MCP tool refresh failed", exc_info=True)
            finally:
                _refreshing.discard(key)

        _touch_cached_tools(cache_key)
        logger.info(
            "MCP tool cache stale for %s — serving %d cached tools and "
            "refreshing in the background",
            cache_key,
            len(cached),
        )
        _in_the_background(_revalidate())
        return cached

    if cached and len(cached) > 0 and (time.time() - cached_ts) < _MCP_TOOL_CACHE_TTL:
        _touch_cached_tools(cache_key)
        redis_set = await run_redis(cache_smembers, auth_set_key)
        if redis_set is None:
            return cached
        await run_redis(cache_expire, auth_set_key, _MCP_AUTH_SET_TTL)
        local_set = _cached_connected_set.get(cache_key, set())
        if redis_set == local_set:
            logger.info(
                "MCP tool cache hit (%d tools, %.0fs old, user=%s)",
                len(cached),
                time.time() - cached_ts,
                cache_key or "anonymous",
            )
            return cached
        else:
            logger.info(
                "MCP auth set changed (redis=%s, local=%s), invalidating cache for %s",
                redis_set,
                local_set,
                cache_key,
            )
            _forget_cached_tools(cache_key)

    servers: dict[str, dict[str, Any]] = _get_server_configs()
    enabled: dict[str, dict[str, Any]] = {
        k: v for k, v in servers.items() if v.get("enabled", False)
    }

    enabled = _filter_by_names(enabled, server_names)

    if not enabled:
        logger.warning("No MCP servers enabled")
        return []

    logger.warning(
        "Connecting to %d MCP server(s): %s", len(enabled), ", ".join(enabled)
    )

    pre_discovery_set = (
        await run_redis(cache_smembers, auth_set_key) if cache_key is not None else None
    )

    has_auth: bool = bool(sso_token or user_id)
    discovery_token = _mcp_tool_discovery.set(True)
    try:
        connect_jobs = []
        placeholder_tools: list[list[Any]] = []
        resume_placeholders: dict[str, dict[str, Any]] = {}
        connect_order: list[str] = []
        for name, entry in enabled.items():
            mcp_prefix_name = entry.get("tool_prefix") or name
            bearer = await _resolve_connection_token(name, entry, sso_token, user_id)
            auth_mode = entry.get("auth_mode", "sso")
            if auth_mode in ("oauth", "dcr") and bearer is None:
                logger.info(
                    "[%s] No OAuth token for %s server — using auth placeholder",
                    mcp_prefix_name,
                    auth_mode,
                )
                placeholder_tools.append(
                    prepare_tools_for_model(
                        [_create_auth_placeholder_tool(name, entry)],
                        name,
                    )
                )
                continue

            resume_placeholders[name] = entry
            connect_order.append(name)
            connect_jobs.append(
                _connect_single_server(
                    name=mcp_prefix_name,
                    config=_build_server_config(
                        entry,
                        bearer,
                        _bearer_refresher(name, entry, auth_mode, user_id),
                    ),
                    server_cfg=entry,
                    timeout=entry.get("timeout", 30),
                    required=has_auth,
                    server_key=name,
                )
            )
        results: list[list[Any]] = await asyncio.gather(*connect_jobs)

        for name, tool_list in zip(connect_order, results, strict=False):
            if not tool_list:
                continue
            resume_entry = resume_placeholders.get(name)
            if resume_entry is None:
                continue
            placeholder_tools.append(
                prepare_tools_for_model(
                    [
                        _create_auth_placeholder_tool(
                            name, resume_entry, tools_present=True
                        )
                    ],
                    name,
                )
            )

        results.extend(placeholder_tools)
    finally:
        _mcp_tool_discovery.reset(discovery_token)

    seen: set[str] = set()
    tools: list[Any] = []
    for tool_list in results:
        for tool in tool_list:
            if tool.name not in seen:
                seen.add(tool.name)
                tools.append(tool)
            else:
                logger.warning(f"Duplicate tool '{tool.name}' skipped")

    if not tools:
        oauth_mcps = [
            name
            for name, entry in enabled.items()
            if entry.get("auth_mode") in ("oauth", "dcr")
        ]
        if oauth_mcps:
            logger.warning(
                "All MCP servers failed to load tools — connect OAuth first: %s",
                ", ".join(f"POST /mcp/{n}/connect" for n in oauth_mcps),
            )
        elif sso_token:
            logger.warning("All MCP servers failed to load tools (token present)")
        else:
            logger.warning("MCP tools deferred — no auth token at startup")
        return []

    if cache_key is not None:
        _store_cached_tools(
            cache_key,
            tools,
            pre_discovery_set
            if pre_discovery_set is not None
            else _cached_connected_set.get(cache_key, set()),
        )
    logger.info(
        "Loaded %d MCP tool(s): %s (cached for %.0fs, user=%s)",
        len(tools),
        ", ".join(seen),
        _MCP_TOOL_CACHE_TTL,
        cache_key or "anonymous",
    )
    _log_tool_budget(tools)
    return tools


_TOOL_BUDGET_WARN = int(os.environ.get("MCP_TOOL_BUDGET_WARN", "120"))
_APPROX_TOKENS_PER_TOOL = settings.MCP_APPROX_TOKENS_PER_TOOL


def _log_tool_budget(tools: list[Any]) -> None:
    """Report the prompt cost of the bound tool set, per server."""
    if not tools:
        return

    by_server: dict[str, int] = {}
    chars_by_server: dict[str, int] = {}
    for tool in tools:
        name = getattr(tool, "name", "") or ""
        metadata = getattr(tool, "metadata", None)
        server = None
        if isinstance(metadata, dict):
            server = metadata.get("mcp_server")
        if not server:
            parts = name.split("__")
            server = parts[1] if len(parts) >= 2 and parts[0] == "mcp" else None
        server = server or "(built-in)"
        by_server[server] = by_server.get(server, 0) + 1
        size = len(name) + len(str(getattr(tool, "description", "") or ""))
        schema = getattr(tool, "args_schema", None)
        if schema is not None:
            size += len(str(schema))
        chars_by_server[server] = chars_by_server.get(server, 0) + size

    total = len(tools)
    estimate = total * _APPROX_TOKENS_PER_TOOL
    breakdown = ", ".join(
        f"{server}={by_server[server]}t/{chars // 4}tok"
        for server, chars in sorted(chars_by_server.items(), key=lambda kv: -kv[1])
    )

    if total >= _TOOL_BUDGET_WARN:
        logger.warning(
            "Tool budget: %d tools ≈ %d input tokens per model call, "
            "paid on every turn whether used or not. Breakdown: %s. "
            "Scope servers per subagent to cut this — see "
            "docs/operations/scalability.md.",
            total,
            estimate,
            breakdown,
        )
    else:
        logger.info(
            "Tool budget: %d tools ≈ %d input tokens per call (%s)",
            total,
            estimate,
            breakdown,
        )
