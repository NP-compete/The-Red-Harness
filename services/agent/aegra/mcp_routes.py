"""HTTP routes for per-MCP OAuth/DCR connect, callback, status, disconnect, and Apps host proxy."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict

from agent.src.agent.config import agent_config
from agent.src.security.credential_presence import credential_state
from agent.src.settings import settings

router = APIRouter(tags=["mcp"])


class IconResponse(Response):
    """Declares the media type the icon route actually sends."""

    media_type = "image/*"


class McpServerOut(BaseModel):
    """One configured server, with no secret in it."""

    model_config = ConfigDict(extra="allow")

    name: str
    url: str = ""
    display_name: str = ""
    description: str = ""
    has_icon: bool = False
    transport: str = ""
    enabled: bool = True
    auth_mode: str = ""
    credential: str = ""
    tool_prefix: str = ""


class McpServersOut(BaseModel):
    """Every MCP server, with where it points and how it authenticates."""

    servers: list[McpServerOut]
    enabled_count: int
    reregister_enabled: bool


class McpConnectionOut(BaseModel):
    """One person's connection to one MCP server."""

    mcp_name: str
    auth_mode: str = ""
    description: str = ""
    display_name: str = ""
    connected: bool
    account: str | None = None

    model_config = ConfigDict(extra="allow")


class McpConnectionsOut(BaseModel):
    """Every MCP server this person has connected."""

    connections: list[McpConnectionOut]


class McpConnectStartedOut(BaseModel):
    """Where to send somebody to finish connecting a server."""

    authorize_url: str


class McpStatusOut(BaseModel):
    """Whether this person is connected to one server."""

    mcp_name: str
    connected: bool


class McpReregisteredOut(BaseModel):
    """What re-registering an OAuth client changed."""

    mcp_name: str
    re_registered: bool
    client_id: str | None = None


class McpCapabilitiesOut(BaseModel):
    """How many tools, resources and prompts a server exposes."""

    mcp_name: str
    tools: int | None = None
    resources: int | None = None
    prompts: int | None = None


class McpInventoryItemOut(BaseModel):
    """One thing a server offers: a tool, a resource or a prompt."""

    model_config = ConfigDict(extra="allow")

    name: str = ""
    description: str = ""


class McpInventoryOut(BaseModel):
    """Everything one MCP server offers."""

    mcp_name: str
    tools: list[McpInventoryItemOut] = []
    resources: list[McpInventoryItemOut] = []
    prompts: list[McpInventoryItemOut] = []


class McpToolsListOut(BaseModel):
    """The MCP specification's `tools/list` result, passed through."""

    model_config = ConfigDict(extra="allow")

    tools: list[dict[str, Any]] = []
    nextCursor: str | None = None  # noqa: N815 - the wire name


class McpResourcesListOut(BaseModel):
    """The MCP specification's `resources/list` result, passed through."""

    model_config = ConfigDict(extra="allow")

    resources: list[dict[str, Any]] = []
    nextCursor: str | None = None  # noqa: N815 - the wire name


class McpResourceTemplatesListOut(BaseModel):
    """The MCP specification's `resources/templates/list` result."""

    model_config = ConfigDict(extra="allow")

    resourceTemplates: list[dict[str, Any]] = []  # noqa: N815 - the wire name
    nextCursor: str | None = None  # noqa: N815 - the wire name


class McpResourceReadOut(BaseModel):
    """The MCP specification's `resources/read` result, passed through."""

    model_config = ConfigDict(extra="allow")

    contents: list[dict[str, Any]] = []


class McpToolCallOut(BaseModel):
    """The MCP specification's `tools/call` result, passed through."""

    model_config = ConfigDict(extra="allow")

    content: list[dict[str, Any]] = []
    isError: bool | None = None  # noqa: N815 - the wire name


async def _authenticated_user_id(request: Request) -> str:
    """Return the SSO ``sub`` from the incoming Bearer token."""
    from agent.aegra.auth import (
        DEV_USER_ID,
        ENABLE_AUTH,
        ENVIRONMENT,
        _decode_token,
    )
    from agent.utils.pylogger import get_python_logger

    logger = get_python_logger()

    if ENVIRONMENT == "production" and not ENABLE_AUTH:
        raise HTTPException(
            status_code=500, detail="Authentication bypass disabled in production"
        )

    if not ENABLE_AUTH:
        logger.warning("Auth bypass active for MCP routes (development mode)")
        return DEV_USER_ID

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )

    payload = _decode_token(auth_header[7:])
    return str(payload["sub"])


def _sso_bearer_from_request(request: Request) -> str | None:
    """Return the raw Bearer token (SSO access token) when present."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip() or None
    return None


def _http_exception_response(exc: HTTPException) -> JSONResponse | None:
    """Return JSONResponse for dict ``detail`` so aegra does not stringify-fail."""
    detail: Any = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return None


@router.post(
    "/mcp/{mcp_name}/connect", responses={200: {"model": McpConnectStartedOut}}
)
async def mcp_connect(mcp_name: str, request: Request) -> JSONResponse:
    """Start OAuth/DCR authorization for an MCP server."""
    from agent.aegra.mcp_oauth_handlers import handle_mcp_connect
    from agent.src.agent.config import agent_config
    from agent.src.settings import settings

    servers = agent_config.get_mcp_servers()
    cfg = servers.get(mcp_name, {})
    if cfg.get("auth_mode") == "dcr" and not settings.MCP_DCR_ENABLED:
        return JSONResponse(
            status_code=403,
            content={"detail": "DCR is disabled"},
        )

    user_id = await _authenticated_user_id(request)
    caller_origin = request.headers.get("origin")
    result = await handle_mcp_connect(user_id, mcp_name, caller_origin=caller_origin)
    return JSONResponse(content=result)


@router.get(
    "/mcp/oauth/callback",
    response_class=HTMLResponse,
    responses={
        200: {
            "content": {"text/html": {"schema": {"type": "string"}}},
            "description": "A page that notifies the window which started the flow.",
        }
    },
)
async def mcp_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
) -> HTMLResponse:
    """Handle the OAuth redirect — exchange code and notify the UI opener."""
    from agent.aegra.mcp_oauth_handlers import handle_mcp_oauth_callback

    return await handle_mcp_oauth_callback(code, state, request)


@router.get("/mcp/oauth/connections", responses={200: {"model": McpConnectionsOut}})
async def mcp_connections(request: Request) -> JSONResponse:
    """Return OAuth/DCR MCP connection status for the current user."""
    from agent.aegra.mcp_oauth_handlers import handle_mcp_connections

    user_id = await _authenticated_user_id(request)
    result = await handle_mcp_connections(user_id)
    return JSONResponse(content=result)


class OAuthClientOut(BaseModel):
    """This agent's OAuth client, as a document (CIMD)."""

    model_config = ConfigDict(extra="allow")

    client_id: str
    client_name: str = ""
    client_uri: str = ""
    redirect_uris: list[str] = []
    grant_types: list[str] = []
    response_types: list[str] = []
    token_endpoint_auth_method: str = ""


@router.get("/.well-known/oauth-client", responses={200: {"model": OAuthClientOut}})
async def oauth_client_metadata() -> JSONResponse:
    """This agent's OAuth client, as a document (CIMD)."""
    from agent.src.settings import settings as _settings

    base = _settings.agent_public_base_url
    document = {
        "client_id": f"{base}/.well-known/oauth-client",
        "client_name": _settings.agent_deployment_id or "Agent",
        "client_uri": base,
        "redirect_uris": [_settings.oauth_callback_url],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }
    return JSONResponse(content=document)


_ICON_CACHE: dict[str, tuple[bytes, str]] = {}

_MAX_ICON_BYTES = settings.MCP_MAX_ICON_BYTES

_MAX_ICON_HOPS = 5


async def fetch_icon(client: Any, url: str) -> tuple[bytes, str] | None:
    """Fetch an icon, checking every hop before following it."""
    from urllib.parse import urlparse

    from agent.src.security.url_safety import check_url
    from agent.utils.pylogger import get_python_logger

    logger = get_python_logger()

    try:
        allowed = [(urlparse(url.strip()).hostname or "").lower()]
    except ValueError:
        return None
    if not allowed[0]:
        return None

    import httpx

    current = url.strip()
    seen: set[str] = set()

    for _ in range(_MAX_ICON_HOPS):
        checked = check_url(current, allowed_hosts=allowed)
        if not checked.ok:
            logger.warning("Refusing an icon from %s: %s", current, checked.reason)
            return None
        if current in seen:
            logger.warning("Refusing an icon from %s: the redirects loop", url)
            return None
        seen.add(current)

        reply = await client.get(current, headers={"User-Agent": "Mozilla/5.0"})
        if not getattr(reply, "is_redirect", False):
            if reply.status_code >= 400 or len(reply.content) > _MAX_ICON_BYTES:
                return None
            media = reply.headers.get("content-type", "image/x-icon").split(";")[0]
            if not media.startswith("image/"):
                return None
            return reply.content, media

        location = reply.headers.get("location")
        if not location:
            return None
        current = str(httpx.URL(current).join(location))

    logger.warning("Refusing an icon from %s: too many redirects", url)
    return None


@router.get(
    "/mcp/{mcp_name}/icon",
    response_class=IconResponse,
    responses={
        200: {
            "content": {"image/*": {"schema": {"type": "string", "format": "binary"}}},
            "description": "The server's icon, proxied from this origin.",
        }
    },
)
async def mcp_icon(mcp_name: str, request: Request) -> Response:
    """Serve a server's icon from this origin."""
    await _authenticated_user_id(request)

    from agent.src.agent.config import agent_config

    cached = _ICON_CACHE.get(mcp_name)
    if cached is None:
        cfg = (agent_config.get_mcp_servers() or {}).get(mcp_name) or {}
        url = str(cfg.get("icon") or "")
        if not url.startswith("https://"):
            raise HTTPException(status_code=404, detail="No icon for this server")

        import httpx

        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                found = await fetch_icon(client, url)
            if found is None:
                raise HTTPException(status_code=404, detail="Icon unavailable")
            cached = found
            _ICON_CACHE[mcp_name] = cached
        except HTTPException:
            raise
        except Exception as exc:
            from agent.utils.pylogger import get_python_logger

            get_python_logger().debug("Icon fetch failed for %s: %s", mcp_name, exc)
            raise HTTPException(status_code=404, detail="Icon unavailable") from None

    body, media = cached
    return Response(
        content=body,
        media_type=media,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/mcp/servers", responses={200: {"model": McpServersOut}})
async def mcp_servers(request: Request) -> JSONResponse:
    """Every configured MCP server, enabled or not."""
    await _authenticated_user_id(request)

    from agent.src.agent.config import agent_config

    try:
        servers = agent_config.get_mcp_servers() or {}
    except Exception as exc:
        from agent.utils.pylogger import get_python_logger

        get_python_logger().warning("Could not read MCP servers: %s", exc)
        servers = {}

    listed = [
        {
            "name": name,
            "url": cfg.get("url", ""),
            "display_name": cfg.get("display_name") or name,
            "description": cfg.get("description", ""),
            "has_icon": bool(cfg.get("icon")),
            "transport": cfg.get("transport", ""),
            "enabled": bool(cfg.get("enabled", False)),
            "auth_mode": cfg.get("auth_mode", "dcr")
            if cfg.get("auth", True)
            else "none",
            "credential": credential_state(cfg),
            "tool_prefix": cfg.get("tool_prefix") or name,
        }
        for name, cfg in servers.items()
        if isinstance(cfg, dict)
    ]
    listed.sort(key=lambda s: s["display_name"].lower())

    from agent.src.settings import settings as _settings

    return JSONResponse(
        content={
            "servers": listed,
            "enabled_count": sum(1 for s in listed if s["enabled"]),
            "reregister_enabled": bool(_settings.ENABLE_DCR_REREGISTER_API),
        }
    )


@router.post(
    "/mcp/{mcp_name}/reregister", responses={200: {"model": McpReregisteredOut}}
)
async def mcp_reregister(mcp_name: str, request: Request) -> JSONResponse:
    """Delete stale DCR client credentials and re-register with current config URLs."""
    from agent.aegra.mcp_oauth_handlers import handle_mcp_reregister
    from agent.src.settings import settings

    if not settings.ENABLE_DCR_REREGISTER_API:
        return JSONResponse(
            status_code=403,
            content={"detail": "DCR re-register API is disabled"},
        )

    servers = agent_config.get_mcp_servers()
    cfg = servers.get(mcp_name, {})
    if cfg.get("auth_mode") == "dcr" and not settings.MCP_DCR_ENABLED:
        return JSONResponse(
            status_code=403,
            content={"detail": "DCR is disabled"},
        )

    from agent.aegra.auth_helpers import check_ldap_role

    await check_ldap_role(request, developer_only=True)
    result = await handle_mcp_reregister(mcp_name)
    return JSONResponse(content=result)


@router.get("/mcp/{mcp_name}/status", responses={200: {"model": McpStatusOut}})
async def mcp_status(mcp_name: str, request: Request) -> JSONResponse:
    """Return whether the current user has a valid token for the MCP."""
    from agent.aegra.mcp_oauth_handlers import handle_mcp_status

    user_id = await _authenticated_user_id(request)
    result = await handle_mcp_status(user_id, mcp_name)
    return JSONResponse(content=result)


@router.delete("/mcp/{mcp_name}/disconnect", responses={200: {"model": McpStatusOut}})
async def mcp_disconnect(mcp_name: str, request: Request) -> JSONResponse:
    """Clear stored OAuth tokens for an MCP server for the current user."""
    from agent.aegra.mcp_oauth_handlers import handle_mcp_disconnect

    user_id = await _authenticated_user_id(request)
    result = await handle_mcp_disconnect(user_id, mcp_name)
    return JSONResponse(content=result)


@router.get("/info")
async def get_agent_info() -> dict[str, Any]:
    """Who this is, which build is answering, and what it connects to."""
    from agent.aegra.mcp_oauth_handlers import _interactive_oauth_servers
    from agent.version import version

    oauth_mcps = [name for name, _ in _interactive_oauth_servers()]
    return {
        "name": agent_config.get_name(),
        "version": version(),
        "oauth_mcps": oauth_mcps,
    }


@router.get(
    "/mcp/{mcp_name}/capabilities", responses={200: {"model": McpCapabilitiesOut}}
)
async def mcp_capabilities(mcp_name: str, request: Request) -> JSONResponse:
    """Counts of tools, resources and prompts for a connected server."""
    from agent.aegra.mcp_host import count_capabilities

    user_id = await _authenticated_user_id(request)
    try:
        counts = await count_capabilities(
            mcp_name,
            user_id=user_id,
            sso_token=_sso_bearer_from_request(request),
        )
    except HTTPException as exc:
        as_json = _http_exception_response(exc)
        if as_json is not None:
            return as_json
        raise
    except Exception as exc:
        from agent.utils.pylogger import get_python_logger

        get_python_logger().info(
            "Could not read capabilities for '%s': %s", mcp_name, exc
        )
        counts = {"tools": None, "resources": None, "prompts": None}

    return JSONResponse(content={"mcp_name": mcp_name, **counts})


@router.get("/mcp/{mcp_name}/inventory", responses={200: {"model": McpInventoryOut}})
async def mcp_inventory(mcp_name: str, request: Request) -> JSONResponse:
    """What a connected server actually offers, with descriptions."""
    from agent.aegra.mcp_host import inventory

    user_id = await _authenticated_user_id(request)
    try:
        found = await inventory(
            mcp_name, user_id=user_id, sso_token=_sso_bearer_from_request(request)
        )
    except HTTPException as exc:
        as_json = _http_exception_response(exc)
        if as_json is not None:
            return as_json
        raise
    return JSONResponse(content={"mcp_name": mcp_name, **found})


@router.post("/mcp/{mcp_name}/tools/list", responses={200: {"model": McpToolsListOut}})
async def mcp_tools_list(mcp_name: str, request: Request) -> JSONResponse:
    """Proxy MCP ``tools/list`` for Apps host metadata (stateless)."""
    from agent.aegra.mcp_host import list_tools

    user_id = await _authenticated_user_id(request)
    cursor: str | None = None
    try:
        body = await request.json()
    except Exception:
        body = {}
    if body is not None and not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    if isinstance(body, dict):
        raw_cursor = body.get("cursor")
        if raw_cursor is not None and not isinstance(raw_cursor, str):
            raise HTTPException(status_code=400, detail="cursor must be a string")
        cursor = raw_cursor

    try:
        result = await list_tools(
            mcp_name,
            cursor=cursor,
            user_id=user_id,
            sso_token=_sso_bearer_from_request(request),
        )
    except HTTPException as exc:
        as_json = _http_exception_response(exc)
        if as_json is not None:
            return as_json
        raise
    return JSONResponse(content=result)


@router.post(
    "/mcp/{mcp_name}/resources/list", responses={200: {"model": McpResourcesListOut}}
)
async def mcp_resources_list(mcp_name: str, request: Request) -> JSONResponse:
    """Proxy MCP ``resources/list`` for Apps Views (stateless)."""
    from agent.aegra.mcp_host import list_resources

    user_id = await _authenticated_user_id(request)
    cursor: str | None = None
    try:
        body = await request.json()
    except Exception:
        body = {}
    if body is not None and not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    if isinstance(body, dict):
        raw_cursor = body.get("cursor")
        if raw_cursor is not None and not isinstance(raw_cursor, str):
            raise HTTPException(status_code=400, detail="cursor must be a string")
        cursor = raw_cursor

    try:
        result = await list_resources(
            mcp_name,
            cursor=cursor,
            user_id=user_id,
            sso_token=_sso_bearer_from_request(request),
        )
    except HTTPException as exc:
        as_json = _http_exception_response(exc)
        if as_json is not None:
            return as_json
        raise
    return JSONResponse(content=result)


@router.post(
    "/mcp/{mcp_name}/resources/templates/list",
    responses={200: {"model": McpResourceTemplatesListOut}},
)
async def mcp_resource_templates_list(mcp_name: str, request: Request) -> JSONResponse:
    """Proxy MCP ``resources/templates/list`` for Apps Views (stateless)."""
    from agent.aegra.mcp_host import list_resource_templates

    user_id = await _authenticated_user_id(request)
    cursor: str | None = None
    try:
        body = await request.json()
    except Exception:
        body = {}
    if body is not None and not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")
    if isinstance(body, dict):
        raw_cursor = body.get("cursor")
        if raw_cursor is not None and not isinstance(raw_cursor, str):
            raise HTTPException(status_code=400, detail="cursor must be a string")
        cursor = raw_cursor

    try:
        result = await list_resource_templates(
            mcp_name,
            cursor=cursor,
            user_id=user_id,
            sso_token=_sso_bearer_from_request(request),
        )
    except HTTPException as exc:
        as_json = _http_exception_response(exc)
        if as_json is not None:
            return as_json
        raise
    return JSONResponse(content=result)


@router.post(
    "/mcp/{mcp_name}/resources/read", responses={200: {"model": McpResourceReadOut}}
)
async def mcp_resources_read(mcp_name: str, request: Request) -> JSONResponse:
    """Proxy MCP ``resources/read`` for Apps (any resource URI; stateless)."""
    from agent.aegra.mcp_host import read_resource

    user_id = await _authenticated_user_id(request)
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")

    uri = body.get("uri")
    try:
        result = await read_resource(
            mcp_name,
            uri if isinstance(uri, str) else "",
            user_id=user_id,
            sso_token=_sso_bearer_from_request(request),
        )
    except HTTPException as exc:
        as_json = _http_exception_response(exc)
        if as_json is not None:
            return as_json
        raise
    return JSONResponse(content=result)


@router.post("/mcp/{mcp_name}/tools/call", responses={200: {"model": McpToolCallOut}})
async def mcp_tools_call(mcp_name: str, request: Request) -> JSONResponse:
    """Proxy MCP ``tools/call`` for app-initiated tools (stateless)."""
    from agent.aegra.mcp_host import call_app_tool

    user_id = await _authenticated_user_id(request)
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON body must be an object")

    tool_name = body.get("name")
    arguments = body.get("arguments")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise HTTPException(
            status_code=400, detail="arguments must be a JSON object when provided"
        )

    try:
        result = await call_app_tool(
            mcp_name,
            tool_name if isinstance(tool_name, str) else "",
            arguments,
            user_id=user_id,
            sso_token=_sso_bearer_from_request(request),
        )
    except HTTPException as exc:
        as_json = _http_exception_response(exc)
        if as_json is not None:
            return as_json
        raise
    return JSONResponse(content=result)
