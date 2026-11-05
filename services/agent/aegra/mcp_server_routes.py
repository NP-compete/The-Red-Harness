"""The door another system calls this agent through."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from agent.src.agent.config.tool_projection import project_tools, scope_of
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

router = APIRouter(tags=["mcp-server"])

PROTOCOL_VERSION = "2025-06-18"

_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602


class RpcErrorOut(BaseModel):
    """A JSON-RPC error, with its code and message."""

    code: int
    message: str


class JsonRpcOut(BaseModel):
    """One JSON-RPC envelope: `result` or `error`, never both."""

    model_config = ConfigDict(extra="allow")

    jsonrpc: str = "2.0"
    id: Any = None
    result: dict[str, Any] | None = None
    error: RpcErrorOut | None = None


@router.post("/mcp/server", responses={200: {"model": JsonRpcOut}})
async def mcp_server(request: Request) -> Any:
    """One JSON-RPC endpoint, over the run API underneath."""
    from agent.src.agent.config import agent_config

    door = agent_config.get_inbound_config()
    if not door.enabled:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    body = await request.json()
    rpc_id = body.get("id")
    method = str(body.get("method") or "")
    params = body.get("params") or {}

    if method == "initialize":
        return _ok(rpc_id, _hello())

    caller = await _caller(request)
    if not caller:
        return JSONResponse(
            status_code=401,
            content={"detail": "This door is open to identified callers only"},
        )

    if method == "tools/list":
        return _ok(rpc_id, {"tools": project_tools(door.tools)})

    if method == "tools/call":
        return _ok(
            rpc_id, await _call(params, door=door, caller=caller, request=request)
        )

    return _error(rpc_id, _METHOD_NOT_FOUND, f"Unknown method {method!r}")


def _hello() -> dict[str, Any]:
    """The initialize reply: protocol version, capabilities and server info."""
    from agent.src.agent.config import agent_config

    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": agent_config.get_name() or "agent", "version": "1"},
    }


async def _call(
    params: dict[str, Any], *, door: Any, caller: str, request: Request
) -> dict[str, Any]:
    """Run one published tool and return the JSON-RPC result."""
    name = str(params.get("name") or "")
    arguments = params.get("arguments") or {}

    scope = scope_of(name, door.tools)
    if scope is None:
        return _tool_error(f"{name!r} is not a tool this agent publishes")

    question = str(arguments.get("question") or "").strip()
    if not question:
        return _tool_error("A call needs a 'question' to ask")

    from agent.src.security.inbound_authority import (
        AuthorityRefused,
        authority_for,
    )

    try:
        authority = authority_for(mode=door.auth_mode, caller=caller, scope=scope)
    except AuthorityRefused as refused:
        return _tool_error(str(refused))

    try:
        found = await _run(
            caller=caller,
            question=question,
            thread_id=str(arguments.get("thread_id") or ""),
            scope=scope,
            authorization=request.headers.get("authorization", ""),
            metadata=authority.as_metadata(),
        )
    except Exception as error:
        logger.warning("An inbound call failed: %s", error)
        return _tool_error(f"The run failed: {error}")

    waiting = found.get("paused")
    if waiting:
        return {
            "content": [{"type": "text", "text": _describe(waiting)}],
            "structuredContent": {
                "status": "awaiting_decision",
                "thread_id": found.get("thread_id", ""),
                "awaiting": waiting.get("awaiting", []),
            },
            "isError": False,
        }

    return {
        "content": [{"type": "text", "text": found.get("text", "")}],
        "structuredContent": {
            "status": "answered",
            "thread_id": found.get("thread_id", ""),
        },
        "isError": False,
    }


def _describe(waiting: dict[str, Any]) -> str:
    """What is waiting, in a sentence a program can also parse."""
    actions = ", ".join(
        str(entry.get("action") or "") for entry in waiting.get("awaiting") or []
    )
    return (
        f"This run is waiting for a decision on: {actions or 'an action'}. "
        f"Continue conversation {waiting.get('thread_id', '')} to approve or reject it."
    )


async def _caller(request: Request) -> str:
    """The verified identity of whoever is calling, or nothing."""
    from agent.aegra.inbound_limit_middleware import caller_of

    return await caller_of(request)


def _own_address() -> str:
    """Where this process is answering the run API."""
    import os

    return f"http://127.0.0.1:{os.getenv('AGENT_PORT', '5002')}"


async def _run(
    *,
    caller: str,
    question: str,
    thread_id: str,
    scope: str,
    authorization: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ask the agent, through the same API every other client uses."""
    import httpx

    from agent.cli.outcome import answer_from
    from agent.src.agent.config.inbound_pause import paused_result

    headers = {"Authorization": authorization} if authorization else {}

    async with httpx.AsyncClient(
        base_url=_own_address(), timeout=None, headers=headers
    ) as client:
        conversation = thread_id
        if not conversation:
            made = await client.post("/threads", json={})
            made.raise_for_status()
            conversation = made.json()["thread_id"]

        reply = await client.post(
            f"/threads/{conversation}/runs/wait",
            json={
                "assistant_id": "agent",
                "input": {"messages": [{"role": "user", "content": question}]},
                "metadata": {**(metadata or {}), "inbound_scope": scope},
            },
        )
        reply.raise_for_status()
        state = reply.json()

    waiting = paused_result(state, thread_id=conversation)
    return {
        "text": answer_from(state) or "",
        "thread_id": conversation,
        "paused": waiting,
    }


def _ok(rpc_id: Any, result: dict[str, Any]) -> JSONResponse:
    """A JSON-RPC success envelope."""
    return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})


def _error(rpc_id: Any, code: int, message: str) -> JSONResponse:
    """A JSON-RPC error envelope."""
    return JSONResponse(
        {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}
    )


def _tool_error(message: str) -> dict[str, Any]:
    """A tool result carrying an error message."""
    return {
        "content": [{"type": "text", "text": message}],
        "isError": True,
    }
