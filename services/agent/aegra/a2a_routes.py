"""Being discovered and delegated to by another agent."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(tags=["a2a"])

PROTOCOL_VERSION = "0.3.0"

_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602


class AgentCardOut(BaseModel):
    """The A2A agent card, as the specification names its fields."""

    model_config = {"extra": "allow"}

    protocolVersion: str  # noqa: N815 - the wire name
    name: str
    description: str = ""
    url: str = ""
    preferredTransport: str = ""  # noqa: N815 - the wire name
    version: str = ""
    capabilities: dict[str, Any] = {}
    defaultInputModes: list[str] = []  # noqa: N815 - the wire name
    defaultOutputModes: list[str] = []  # noqa: N815 - the wire name
    skills: list[dict[str, Any]] = []
    securitySchemes: dict[str, Any] = {}  # noqa: N815 - the wire name
    security: list[dict[str, Any]] = []
    supportsAuthenticatedExtendedCard: bool = False  # noqa: N815 - the wire name


@router.get("/.well-known/agent-card.json", responses={200: {"model": AgentCardOut}})
async def agent_card(request: Request) -> Any:
    """What this agent is, and how to talk to it."""
    from agent.src.agent.config import agent_config

    door = agent_config.get_inbound_config()
    if not door.enabled:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    caller = await _caller(request)
    return JSONResponse(
        _card(door, base=str(request.base_url).rstrip("/"), full=bool(caller))
    )


def _card(door: Any, *, base: str, full: bool) -> dict[str, Any]:
    """The agent card, abbreviated or full."""
    from agent.src.agent.config import agent_config

    name = agent_config.get_name() or "agent"
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "name": name,
        "description": f"{name}, reachable as a peer",
        "url": f"{base}/a2a",
        "preferredTransport": "JSONRPC",
        "version": "1",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": tool.name,
                "name": tool.name,
                "description": tool.description,
                "tags": [tool.scope],
            }
            for tool in door.tools
        ]
        if full
        else [],
        "securitySchemes": {
            "bearer": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        },
        "security": [{"bearer": []}],
        "supportsAuthenticatedExtendedCard": True,
    }


class A2aRpcErrorOut(BaseModel):
    """A JSON-RPC error, with its code and message."""

    code: int
    message: str


class A2aRpcOut(BaseModel):
    """One JSON-RPC envelope: `result` or `error`, never both."""

    model_config = {"extra": "allow"}

    jsonrpc: str = "2.0"
    id: Any = None
    result: dict[str, Any] | None = None
    error: A2aRpcErrorOut | None = None


@router.post("/a2a", responses={200: {"model": A2aRpcOut}})
async def a2a(request: Request) -> Any:
    """One JSON-RPC endpoint for delegated work."""
    from agent.src.agent.config import agent_config

    door = agent_config.get_inbound_config()
    if not door.enabled:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    body = await request.json()
    rpc_id = body.get("id")
    method = str(body.get("method") or "")

    caller = await _caller(request)
    if not caller:
        return JSONResponse(
            status_code=401,
            content={"detail": "This door is open to identified peers only"},
        )

    if method != "message/send":
        return _error(rpc_id, _METHOD_NOT_FOUND, f"Unknown method {method!r}")

    return await _delegate(
        body.get("params") or {},
        rpc_id=rpc_id,
        door=door,
        caller=caller,
        request=request,
    )


async def _delegate(
    params: dict[str, Any],
    *,
    rpc_id: Any,
    door: Any,
    caller: str,
    request: Request,
) -> Any:
    """Run a delegated A2A message and return the JSON-RPC reply."""
    from agent.src.security.inbound_authority import (
        AuthorityRefused,
        authority_for,
    )

    message = params.get("message") or {}
    question = _text_of(message.get("parts") or [])
    if not question:
        return _error(rpc_id, _INVALID_PARAMS, "A task needs something to act on")

    scope = (
        "act" if all(t.scope == "act" for t in door.tools) and door.tools else "read"
    )

    try:
        authority = authority_for(mode=door.auth_mode, caller=caller, scope=scope)
    except AuthorityRefused as refused:
        return _error(rpc_id, _INVALID_PARAMS, str(refused))

    try:
        found = await _run(
            caller=caller,
            question=question,
            thread_id=str(params.get("contextId") or ""),
            scope=scope,
            authorization=request.headers.get("authorization", ""),
            metadata=authority.as_metadata(),
        )
    except Exception as error:
        logger.warning("A delegated task failed: %s", error)
        return _error(rpc_id, _INVALID_PARAMS, f"The task failed: {error}")

    waiting = found.get("paused")
    if waiting:
        return _ok(
            rpc_id,
            {
                "kind": "task",
                "id": found.get("thread_id", ""),
                "contextId": found.get("thread_id", ""),
                "status": {
                    "state": "input-required",
                    "message": {
                        "kind": "message",
                        "role": "agent",
                        "messageId": f"{found.get('thread_id', '')}-waiting",
                        "parts": [{"kind": "text", "text": _describe(waiting)}],
                    },
                },
            },
        )

    return _ok(
        rpc_id,
        {
            "kind": "message",
            "role": "agent",
            "messageId": f"{found.get('thread_id', '')}-reply",
            "contextId": found.get("thread_id", ""),
            "parts": [{"kind": "text", "text": found.get("text", "")}],
        },
    )


def _text_of(parts: list[Any]) -> str:
    """The text parts of an A2A message, joined."""
    return " ".join(
        str(part.get("text") or "")
        for part in parts
        if isinstance(part, dict) and part.get("kind") == "text"
    ).strip()


def _describe(waiting: dict[str, Any]) -> str:
    """A plain description of what a paused run is waiting for."""
    from agent.aegra.mcp_server_routes import _describe as said

    return said(waiting)


async def _caller(request: Request) -> str:
    """The caller this request is attributed to."""
    from agent.aegra.inbound_limit_middleware import caller_of

    return await caller_of(request)


async def _run(**kwargs: Any) -> dict[str, Any]:
    """One way in, shared with the other dialect."""
    from agent.aegra.mcp_server_routes import _run as start

    return await start(**kwargs)


def _ok(rpc_id: Any, result: dict[str, Any]) -> JSONResponse:
    """A JSON-RPC success envelope."""
    return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})


def _error(rpc_id: Any, code: int, message: str) -> JSONResponse:
    """A JSON-RPC error envelope."""
    return JSONResponse(
        {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}
    )
