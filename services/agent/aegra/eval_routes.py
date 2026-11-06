"""Eval endpoint for the template agent."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ConfigDict, Field

from agent.aegra.auth_helpers import check_ldap_role
from agent.src.settings import settings


async def _require_developer(request: Request) -> str:
    """Enforce a privileged LDAP role on the operator endpoints."""
    return await check_ldap_role(request, developer_only=True)


async def _check_mcp_auth(request: Request) -> list[dict]:
    """Pre-flight check: return list of MCP servers that need authentication."""
    from agent.aegra.mcp_token_store import McpTokenStore
    from agent.src.agent.config import agent_config
    from agent.src.settings import settings as _settings

    user_id: str = _extract_sub(request) or ""
    log.info("mcp_auth_check: user_id=%r", user_id)
    if not user_id:
        return []

    mcp_servers: dict = agent_config.get_mcp_servers()
    agent_name: str = _settings.agent_deployment_id
    log.info("mcp_auth_check: agent_name=%r", agent_name)

    dcr_servers = {
        name: cfg
        for name, cfg in mcp_servers.items()
        if cfg.get("enabled", True)
        and cfg.get("auth", False)
        and cfg.get("auth_mode", "") in ("dcr", "oauth")
    }
    log.info("mcp_auth_check: dcr_servers=%s", list(dcr_servers.keys()))

    if not dcr_servers:
        return []

    store = McpTokenStore(_settings.database_uri)
    missing: list[dict] = []

    for name, cfg in dcr_servers.items():
        token = await store.get_token(agent_name, user_id, name)
        needs_auth = token is None
        log.info("mcp_auth_check: mcp=%r token_found=%s", name, token is not None)

        if not needs_auth and token and not token.refresh_token:
            from datetime import timedelta, timezone

            min_ttl = timedelta(minutes=_EVAL_TOKEN_MIN_TTL_MINUTES)
            if (
                token.expires_at
                and token.expires_at < datetime.now(timezone.utc) + min_ttl
            ):
                log.info(
                    "mcp_auth_check: mcp=%r token expires at %s (within %d-min buffer, "
                    "no refresh_token)",
                    name,
                    token.expires_at,
                    _EVAL_TOKEN_MIN_TTL_MINUTES,
                )
                needs_auth = True

        if needs_auth:
            missing.append(
                {
                    "name": name,
                    "connect_url": f"/mcp/{name}/connect",
                }
            )

    log.info("mcp_auth_check: missing=%s", [m["name"] for m in missing])
    return missing


_EVAL_TOKEN_MIN_TTL_MINUTES: int = int(
    os.environ.get("EVAL_TOKEN_MIN_TTL_MINUTES", "30")
)

_EVAL_TOKEN_REFRESH_ENABLED: bool = (
    os.environ.get("EVAL_TOKEN_REFRESH_ENABLED", "false").lower() == "true"
)
_EVAL_INTERNAL_TOKEN: str = os.environ.get("EVAL_INTERNAL_TOKEN", "")
_EVAL_KEY_TTL = settings.EVAL_KEY_TTL_SECONDS


def _extract_sub(request: Request) -> str | None:
    """Extract sub from the Bearer JWT in the request without signature verification."""
    from agent.aegra.auth import _decode_sub_unverified

    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return _decode_sub_unverified(auth[7:])


def _stand_in_user() -> str | None:
    """The id threads are owned by when there is no sign-in."""
    from agent.aegra.auth import DEV_USER_ID, ENABLE_AUTH

    return None if ENABLE_AUTH else (DEV_USER_ID or None)


def _extract_username(request: Request) -> str | None:
    """Extract preferred_username from the Bearer JWT (falls back to sub)."""
    import jwt as _jwt

    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = _jwt.decode(auth[7:], options={"verify_signature": False})
        return (
            str(payload.get("preferred_username") or payload.get("sub") or "").strip()
            or None
        )
    except Exception:
        return None


def _write_eval_redis(sub: str, refresh_token: str) -> None:
    """Write the three eval Redis keys at trigger time. Best-effort."""
    if not _EVAL_TOKEN_REFRESH_ENABLED or not sub:
        return
    try:
        from agent.aegra.mcp_crypto import encrypt_secret
        from agent.aegra.redis import cache_set

        cache_set(f"eval:active:{sub}", "1", _EVAL_KEY_TTL)
        if refresh_token:
            encrypted = encrypt_secret(refresh_token)
            if encrypted:
                cache_set(f"eval:refresh:{sub}", encrypted, _EVAL_KEY_TTL)
        cache_set("eval:trigger_sub", sub, _EVAL_KEY_TTL)
    except Exception:
        pass


_HASH_EXTENSIONS = {".md", ".yaml", ".json"}
_HASH_EXCLUDE_DIRS = {"evals", "deployment"}


def _compute_config_hash() -> str:
    """SHA256 of behavior-relevant config files (prompts, skills, runtime, tools)."""
    config_dir = Path(os.environ.get("AGENT_CONFIG_DIR", "config/agent"))
    h = hashlib.sha256()
    if config_dir.exists():
        for fpath in sorted(config_dir.rglob("*")):
            if not fpath.is_file():
                continue
            if fpath.suffix not in _HASH_EXTENSIONS:
                continue
            if any(
                part in _HASH_EXCLUDE_DIRS
                for part in fpath.relative_to(config_dir).parts
            ):
                continue
            h.update(str(fpath.relative_to(config_dir)).encode())
            h.update(fpath.read_bytes())
    return h.hexdigest()[:16]


log = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/eval", tags=["eval"])

_INTERNAL_TOOLS = {
    "write_todos",
    "task",
    "read_file",
    "write_file",
    "ls",
    "grep",
    "glob",
    "execute_command",
    "compact_conversation",
}
MAX_HITL_APPROVALS = settings.EVAL_MAX_HITL_APPROVALS
AGENT_BASE_URL = settings.EVAL_AGENT_BASE_URL
ASSISTANT_ID = settings.EVAL_ASSISTANT_ID


class EvalRunRequest(BaseModel):
    """Request body for a single eval run turn."""

    query: str
    conversation_id: str | None = None
    auto_approve: bool = True


class EvalRunResponse(BaseModel):
    """Response from a single eval run turn."""

    response: str
    pre_approval_response: str | None
    was_interrupted: bool
    tool_calls: list[dict[str, Any]]
    contexts: list[str]
    conversation_id: str


def _extract_from_messages(messages: list[dict]) -> tuple[str, list[dict], list[str]]:
    """Extract response, MCP tool calls, and contexts from state messages (plain dicts)."""
    final_response = ""
    tool_calls: list[dict[str, Any]] = []
    contexts: list[str] = []

    for msg in messages:
        msg_type = msg.get("type", "")

        if msg_type == "ai":
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                final_response = content.strip()
            elif isinstance(content, list):
                text = " ".join(
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ).strip()
                if text:
                    final_response = text

            for tc in msg.get("tool_calls", []):
                name = tc.get("name", "")
                if name and name not in _INTERNAL_TOOLS:
                    tool_calls.append(
                        {
                            "tool_name": name,
                            "arguments": tc.get("args", {}),
                        }
                    )

        elif msg_type == "tool":
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                contexts.append(content.strip())

    return final_response, tool_calls, contexts


async def _create_thread(client: httpx.AsyncClient) -> str:
    resp = await client.post(f"{AGENT_BASE_URL}/threads", json={})
    resp.raise_for_status()
    return resp.json()["thread_id"]  # type: ignore[no-any-return]


async def _run_and_get_state(
    client: httpx.AsyncClient,
    thread_id: str,
    body: dict,
    timeout: float = 120.0,
) -> dict:
    """/runs/wait — returns state with messages at top level + __interrupt__ at top level."""
    resp = await client.post(
        f"{AGENT_BASE_URL}/threads/{thread_id}/runs/wait",
        json={**body, "stream_mode": "values"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def _extract_tool_calls_from_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Extract non-internal tool calls from a list of LangChain messages."""
    tool_calls: list[dict[str, Any]] = []
    for msg in messages:
        msg_dict = (
            msg
            if isinstance(msg, dict)
            else (msg.__dict__ if hasattr(msg, "__dict__") else {})
        )
        if msg_dict.get("type") != "ai":
            continue
        for tc in msg_dict.get("tool_calls", []):
            name = (
                tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
            )
            args = (
                tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            )
            if name and name not in _INTERNAL_TOOLS:
                tool_calls.append({"tool_name": name, "arguments": args})
        if not tool_calls or not any(
            tc["tool_name"] not in _INTERNAL_TOOLS for tc in tool_calls
        ):
            fc = msg_dict.get("additional_kwargs", {}).get("function_call")
            if fc:
                name = fc.get("name", "")
                if name and name not in _INTERNAL_TOOLS:
                    args_raw = fc.get("arguments", "{}")
                    try:
                        args = (
                            json.loads(args_raw)
                            if isinstance(args_raw, str)
                            else args_raw
                        )
                    except Exception:
                        args = {}
                    tool_calls.append({"tool_name": name, "arguments": args})
    return tool_calls


async def _collect_subagent_tool_calls_via_remote_graph(
    thread_id: str,
) -> list[dict[str, Any]]:
    """Fetch subagent tool calls via RemoteGraph.get_state(subgraphs=True)."""
    from langgraph.pregel.remote import RemoteGraph

    tool_calls: list[dict[str, Any]] = []

    try:
        graph = RemoteGraph(ASSISTANT_ID, url=AGENT_BASE_URL)
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        snapshot = await graph.aget_state(config, subgraphs=True)

        def _collect(state_snapshot: Any) -> None:
            tasks = getattr(state_snapshot, "tasks", [])
            for task in tasks:
                substate = getattr(task, "state", None)
                if substate is None:
                    continue
                msgs = getattr(substate, "values", {})
                if isinstance(msgs, dict):
                    msgs = msgs.get("messages", [])
                tool_calls.extend(_extract_tool_calls_from_messages(msgs))
                _collect(substate)

        _collect(snapshot)
    except Exception as exc:
        log.warning(
            "RemoteGraph subgraph fetch failed: %s — falling back to Postgres", exc
        )
        return await _collect_subagent_tool_calls_from_postgres(thread_id)

    return tool_calls


async def _collect_subagent_tool_calls_from_postgres(
    thread_id: str,
) -> list[dict[str, Any]]:
    """Fallback: read subagent tool calls directly from Postgres checkpoint store."""
    import msgpack
    import psycopg

    from agent.src.settings import settings

    def _ext_hook(code: int, data: bytes) -> Any:
        try:
            return msgpack.unpackb(data, raw=False, ext_hook=_ext_hook)
        except Exception:
            return data

    tool_calls: list[dict[str, Any]] = []

    try:
        async with await psycopg.AsyncConnection.connect(settings.database_uri) as conn:
            rows = await conn.execute(
                """
                SELECT DISTINCT ON (checkpoint_ns) blob
                FROM checkpoint_blobs
                WHERE thread_id = %s
                  AND checkpoint_ns != ''
                  AND channel = 'messages'
                ORDER BY checkpoint_ns, version DESC
                """,
                (thread_id,),
            )
            async for (blob,) in rows:
                if blob is None:
                    continue
                try:
                    items = msgpack.unpackb(bytes(blob), raw=False, ext_hook=_ext_hook)
                    if not isinstance(items, (list, tuple)):
                        continue
                    for item in items:
                        if not isinstance(item, (list, tuple)) or len(item) < 3:
                            continue
                        msg = item[2]
                        if not isinstance(msg, dict) or msg.get("type") != "ai":
                            continue
                        tool_calls.extend(_extract_tool_calls_from_messages([msg]))
                except Exception as exc:
                    log.debug("Skipping blob for %s: %s", thread_id, exc)
                    continue
    except Exception as exc:
        log.warning("Postgres subagent tool call extraction failed: %s", exc)

    return tool_calls


def _messages_from_run(run_state: dict) -> list[dict]:
    """Extract messages from /runs/wait response (top-level) or thread state (under values)."""
    if "messages" in run_state:
        return run_state["messages"]  # type: ignore[no-any-return]
    return run_state.get("values", {}).get("messages", [])  # type: ignore[no-any-return]


def _detect_interrupt(run_state: dict) -> bool:
    """Return True if the run state has a pending HITL interrupt."""
    if run_state.get("__interrupt__"):
        return True
    next_nodes = run_state.get("next", [])
    values = run_state.get("values", {})
    return bool(values.get("__interrupt__")) or any(
        "__interrupt__" in str(n) for n in next_nodes
    )


class ThreadToolCallsOut(BaseModel):
    """Which tools a thread's run actually called."""

    model_config = ConfigDict(extra="allow")

    thread_id: str = ""
    tool_calls: list[Any] = []


class ThreadShapeOut(BaseModel):
    """The structure of a thread's messages, without their text."""

    model_config = ConfigDict(extra="allow")

    thread_id: str = ""


class RetrievalEvalOut(BaseModel):
    """How well retrieval answered a set of questions."""

    model_config = ConfigDict(extra="allow")


@router.get(
    "/thread-tool-calls/{thread_id}",
    responses={200: {"model": ThreadToolCallsOut}},
)
async def get_thread_tool_calls(
    thread_id: str,
    request: Request,
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Return all subagent tool calls for a completed thread."""
    await _verify_thread_ownership(thread_id, request)
    tool_calls = await _collect_subagent_tool_calls_from_postgres(thread_id)
    return {"thread_id": thread_id, "tool_calls": tool_calls}


async def _thread_history(thread_id: str, request: Request) -> list[dict[str, Any]]:
    """This thread's checkpoints, newest first."""
    from agent.aegra.fork_routes import _client

    async with _client(request) as client:
        response = await client.get(f"/threads/{thread_id}/history")
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Could not read thread history")
        found = response.json() or []
    return found if isinstance(found, list) else []


@router.get("/thread-shape/{thread_id}", responses={200: {"model": ThreadShapeOut}})
async def get_thread_shape(
    thread_id: str,
    request: Request,
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Whether this conversation was shortened, and by how much."""
    from agent.src.agent.thread_history import (
        high_water_mark,
        shown_messages,
        was_shortened,
    )

    await _verify_thread_ownership(thread_id, request)
    history = await _thread_history(thread_id, request)
    return {
        "thread_id": thread_id,
        "messages_now": len(shown_messages(history)),
        "most_messages": high_water_mark(history),
        "was_shortened": was_shortened(history),
    }


async def _verify_thread_ownership(thread_id: str, request: Request) -> None:
    """Raise 404 unless the authenticated user owns the thread."""
    sub = _extract_sub(request) or _stand_in_user()
    if not sub:
        raise HTTPException(
            status_code=403, detail="Could not identify user from token"
        )

    try:
        async with _pg_conn() as conn:
            row = await conn.execute(
                "SELECT 1 FROM thread WHERE thread_id = %s AND user_id = %s",
                (thread_id, sub),
            )
            if await row.fetchone() is None:
                raise HTTPException(
                    status_code=404, detail=f"Thread '{thread_id}' not found"
                )
    except HTTPException:
        raise
    except Exception as exc:
        log.warning("Thread ownership check failed: %s", exc)
        raise HTTPException(
            status_code=403, detail="Could not verify thread ownership"
        ) from exc


class RetrievalCaseIn(BaseModel):
    """One question, and the documents that answer it."""

    query: str
    relevant: list[str]


class RetrievalCheckIn(BaseModel):
    """What to score: a declared check, or cases given inline."""

    check: str = ""
    cases: list[RetrievalCaseIn] = []
    scope: str = "agent"
    k: int = 8


@router.post("/retrieval", responses={200: {"model": RetrievalEvalOut}})
async def eval_retrieval(
    request: Request,
    body: RetrievalCheckIn,
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Score retrieval against queries whose answers somebody wrote down (E35-T4)."""
    from agent.src.agent.config import agent_config
    from agent.src.evals.retrieval_quality import Case, measure
    from agent.src.knowledge.membership import teams_of
    from agent.src.knowledge.retrieval import retrieve
    from agent.src.knowledge.scopes import Scope, Viewer
    from agent.src.knowledge.store import session_store

    config = agent_config.get_knowledge_config()
    if not config.enabled:
        raise HTTPException(
            status_code=404,
            detail="This deployment keeps no document library, so there is nothing to score.",
        )

    try:
        scope = Scope(body.scope)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"{body.scope!r} is not a scope; try one of "
            + ", ".join(s.value for s in config.scopes),
        ) from None

    from agent.aegra.auth_helpers import memory_user_id

    who = await memory_user_id(request)
    viewer = Viewer(subject=who, teams=await teams_of(who), thread_id=None)
    store = session_store()

    def _search(query: str, k: int) -> list[str]:
        found = retrieve(query, store=store, viewer=viewer, config=config, scope=scope)
        return [hit.document.id for hit in list(found.hits)[:k]]

    from agent.src.agent.config.paths import config_root

    comparison = None
    if body.check:
        from agent.src.evals.declared import declared_registry
        from agent.src.evals.retrieval_runner import run_check

        registry, _problems = declared_registry(config_root())
        try:
            declared = registry.get(body.check)
        except KeyError:
            raise HTTPException(
                status_code=404,
                detail=f"No check named {body.check!r} is declared here.",
            ) from None
        if declared.kind != "retrieval":
            raise HTTPException(
                status_code=422,
                detail=(
                    f"'{declared.name}' is a {declared.kind} check, which is "
                    "scored by reading a transcript rather than by measuring "
                    "which documents came back."
                ),
            )
        try:
            scope = Scope(declared.corpus)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"{declared.corpus!r} is not a scope.",
            ) from None
        try:
            measured, comparison = run_check(
                declared,
                root=config_root(),
                search=_search,
                config=config,
                document_ids=[d.id for d in store.documents_in(scope=scope)],
                registry=registry,
            )
        except ValueError as refused:
            raise HTTPException(status_code=422, detail=str(refused)) from None
    else:
        try:
            cases = [
                Case(query=c.query, relevant=tuple(c.relevant)) for c in body.cases
            ]
            measured = measure(cases, search=_search, corpus=body.scope, k=body.k)
        except ValueError as refused:
            raise HTTPException(status_code=422, detail=str(refused)) from None

    return {
        "corpus": measured.corpus,
        "k": measured.k,
        "recall": round(measured.recall, 3),
        "precision": round(measured.precision, 3),
        "cases": len(measured.cases),
        "variance": round(measured.variance, 3),
        "worst": [
            {
                "query": case.query,
                "recall": round(case.recall, 3),
                "precision": round(case.precision, 3),
                "missed": list(case.missed),
            }
            for case in measured.worst[:5]
        ],
        "against_previous": (
            None
            if comparison is None
            else {
                "difference": round(comparison.difference, 3),
                "significant": comparison.significant,
            }
        ),
    }


@router.post("/run", response_model=EvalRunResponse)
async def eval_run(
    body: EvalRunRequest,
    _token: str = Depends(_require_developer),
) -> EvalRunResponse:
    """Run one conversation turn for eval purposes."""
    conversation_id = body.conversation_id or str(uuid.uuid4())
    pre_approval_response: str | None = None
    was_interrupted = False

    async with httpx.AsyncClient(timeout=120) as client:
        thread_id = await _create_thread(client)

        run_body = {
            "assistant_id": ASSISTANT_ID,
            "input": {"messages": [{"role": "human", "content": body.query}]},
        }

        run_state = await _run_and_get_state(client, thread_id, run_body)
        messages = _messages_from_run(run_state)

        if _detect_interrupt(run_state):
            was_interrupted = True
            for msg in reversed(messages):
                if msg.get("type") == "ai":
                    content = msg.get("content", "")
                    if isinstance(content, str) and content.strip():
                        pre_approval_response = content.strip()
                        break

            if body.auto_approve:
                for _ in range(MAX_HITL_APPROVALS):
                    log.info("Auto-approving HITL interrupt for thread %s", thread_id)
                    approve_body = {
                        "assistant_id": ASSISTANT_ID,
                        "command": {"resume": {"decisions": [{"type": "approve"}]}},
                    }
                    run_state = await _run_and_get_state(
                        client, thread_id, approve_body
                    )
                    if not _detect_interrupt(run_state):
                        break
                else:
                    log.warning(
                        "HITL approval limit reached for thread %s — run may be incomplete",
                        thread_id,
                    )

                messages = _messages_from_run(run_state)

        subagent_tool_calls = await _collect_subagent_tool_calls_via_remote_graph(
            thread_id
        )

    final_response, orchestrator_tool_calls, contexts = _extract_from_messages(messages)
    tool_calls = orchestrator_tool_calls + subagent_tool_calls

    log.info(
        "Eval run complete: thread=%s tools=%d response_len=%d interrupted=%s",
        thread_id,
        len(tool_calls),
        len(final_response),
        was_interrupted,
    )

    return EvalRunResponse(
        response=final_response,
        pre_approval_response=pre_approval_response,
        was_interrupted=was_interrupted,
        tool_calls=tool_calls,
        contexts=contexts,
        conversation_id=conversation_id,
    )


eval_mgmt_router = APIRouter(prefix="/evals", tags=["eval-management"])

_EVALS_DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS evals (
        id              SERIAL PRIMARY KEY,
        config_hash     TEXT NOT NULL,
        eval_status     TEXT NOT NULL DEFAULT 'in_progress',
        eval_score      FLOAT,
        ls_run_ids      TEXT[],
        pass            INTEGER DEFAULT 0,
        fail            INTEGER DEFAULT 0,
        error           INTEGER DEFAULT 0,
        judge_model     TEXT,
        results_detail  JSONB,
        force_reeval    BOOLEAN DEFAULT FALSE,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        completed_at    TIMESTAMPTZ
    )
    """,
    "CREATE INDEX IF NOT EXISTS evals_config_hash ON evals (config_hash)",
    "CREATE INDEX IF NOT EXISTS evals_status ON evals (eval_status)",
    "ALTER TABLE evals ADD COLUMN IF NOT EXISTS ls_run_ids TEXT[]",
    "ALTER TABLE evals DROP COLUMN IF EXISTS ls_run_id",
    "DROP INDEX IF EXISTS evals_ls_run_id",
]


def _pg_conn() -> Any:
    """Borrow a connection from the shared pool."""
    from psycopg.rows import tuple_row

    from agent.src.db.pool import connection

    return connection(row_factory=tuple_row)


async def _execute_ddl(conn: Any, stmt: str) -> None:
    """Run one DDL statement under a short statement timeout."""
    async with conn.transaction():
        await conn.execute("SET LOCAL statement_timeout = '5s'")
        await conn.execute(stmt)


async def _ensure_evals_table() -> None:
    import psycopg.errors

    async with _pg_conn() as conn:
        for stmt in _EVALS_DDL_STATEMENTS:
            try:
                await _execute_ddl(conn, stmt)
            except psycopg.errors.UniqueViolation:
                log.debug("DDL skipped (already exists): %.120s", stmt.strip())
            except Exception as exc:
                log.warning(
                    "evals DDL statement failed: %s | stmt: %.120s", exc, stmt.strip()
                )
                raise


_table_ensured = False


async def _ensure_evals_table_once() -> None:
    global _table_ensured
    if _table_ensured:
        return
    await _ensure_evals_table()
    _table_ensured = True


async def _run_ddl_once(
    ddl: str,
    migrations: list[str],
    flag_attr: str,
    label: str,
) -> None:
    """Generic once-only DDL runner. Updates the module-level bool named flag_attr."""
    import sys as _sys

    import psycopg.errors

    mod = _sys.modules[__name__]
    if getattr(mod, flag_attr):
        return
    try:
        async with _pg_conn() as conn:
            await _execute_ddl(conn, ddl)
            for stmt in migrations:
                try:
                    await _execute_ddl(conn, stmt)
                except psycopg.errors.UndefinedTable:
                    log.info(
                        "%s migration skipped (legacy table absent): %s",
                        label,
                        stmt[:80],
                    )
                except psycopg.errors.UniqueViolation:
                    log.info(
                        "%s migration skipped (data already migrated): %s",
                        label,
                        stmt[:80],
                    )
        setattr(mod, flag_attr, True)
    except Exception as exc:
        log.warning("%s DDL failed: %s", label, exc)
        raise


def _pg_row_to_dict(row: Any, cursor: Any) -> dict[str, Any]:
    return dict(zip([d.name for d in cursor.description], row))


async def _atomic_set_in_progress(
    config_hash: str, force: bool
) -> tuple[dict | None, bool]:
    """Set eval to in_progress in PostgreSQL."""
    await _ensure_evals_table_once()
    now = datetime.now(UTC)

    async with _pg_conn() as conn:
        row = await conn.execute(
            "SELECT * FROM evals WHERE config_hash=%s "
            "AND eval_status='in_progress' ORDER BY created_at DESC LIMIT 1",
            (config_hash,),
        )
        existing = await row.fetchone()
        if existing is not None:
            if force:
                return None, False
            return _pg_row_to_dict(existing, row), False

        cur = await conn.execute(
            """INSERT INTO evals
               (config_hash, eval_status, eval_score, pass, fail, error,
                results_detail, force_reeval, created_at, updated_at, completed_at)
               SELECT %(config_hash)s,'in_progress',
                      NULL,0,0,0,NULL,%(force)s,%(now)s,%(now)s,NULL
               WHERE NOT EXISTS (
                   SELECT 1 FROM evals
                   WHERE config_hash=%(config_hash)s
                   AND eval_status='in_progress'
               )
               RETURNING *""",
            {
                "config_hash": config_hash,
                "force": force,
                "now": now,
            },
        )
        new_row = await cur.fetchone()
        if new_row is None:
            row2 = await conn.execute(
                "SELECT * FROM evals WHERE config_hash=%s "
                "AND eval_status='in_progress' ORDER BY created_at DESC LIMIT 1",
                (config_hash,),
            )
            existing2 = await row2.fetchone()
            if existing2 is not None:
                return _pg_row_to_dict(existing2, row2), False
            return None, False
        doc = _pg_row_to_dict(new_row, cur)
        return doc, True


def _get_config_hash() -> str:
    """Get config hash from env var or compute from config dir."""
    env_hash = os.environ.get("AGENT_CONFIG_HASH")
    if env_hash:
        return env_hash
    return _compute_config_hash()


async def _mark_eval_error(config_hash: str, reason: str, created_at: datetime) -> None:
    """Set the specific in_progress eval record to error."""
    try:
        async with _pg_conn() as conn:
            await conn.execute(
                "UPDATE evals SET eval_status='error', completed_at=NOW(), updated_at=NOW(), "
                "results_detail=%s::jsonb "
                "WHERE config_hash=%s "
                "AND eval_status='in_progress' AND created_at=%s",
                (
                    json.dumps({"error": reason}),
                    config_hash,
                    created_at,
                ),
            )
    except Exception as pg_exc:
        log.warning("Could not mark eval as error: %s", pg_exc)


async def _fire_eval_run(
    config_hash: str,
    auth_token: str = "",
    created_at: datetime | None = None,
    eval_row_id: int | None = None,
) -> str | None:
    """Queue a run for the eval worker to claim.

    Was an HTTP POST to the eval-runner pod. That pod was KEDA
    min=0, so this call could land on something being scaled away,
    and a run lost that way left no trace. Now it writes a row and
    returns: `harness eval-worker` claims it with a lease, and a
    worker that dies mid-run leaves the row reclaimable rather
    than the request failing.

    `auth_token` is no longer forwarded — the worker runs as the
    deployment, not as the caller. Per-user tool credentials were
    never reachable from a min=0 pod in practice.

    Goes through `_pg_conn` like every other query in this module.
    `claims.py` is synchronous because the worker is; here the
    statements are issued directly on the async pooled connection
    rather than reaching for a raw driver handle.
    """
    from agent.src.evals import claims

    try:
        async with _pg_conn() as conn:
            for statement in claims.SCHEMA.strip().split(";"):
                if statement.strip():
                    await _execute_ddl(conn, statement)
            if eval_row_id is None:
                cursor = await conn.execute(
                    "INSERT INTO evals (config_hash, eval_status, force_reeval) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (config_hash, claims.PENDING, False),
                )
                (eval_row_id,) = await cursor.fetchone()
            else:
                await conn.execute(
                    "UPDATE evals SET eval_status = %s WHERE id = %s",
                    (claims.PENDING, eval_row_id),
                )
        log.info("eval_queued id=%s hash=%s", eval_row_id, config_hash)
        return None
    except Exception as exc:  # noqa: BLE001
        msg = f"Could not queue the eval run: {exc}"
        log.warning("eval_queue_failed: %s", msg)
        return msg


_DATASETS_DDL = """
    CREATE TABLE IF NOT EXISTS eval_datasets (
        id          SERIAL PRIMARY KEY,
        dataset     JSONB NOT NULL,
        judge_model TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
"""
_DATASETS_DDL_MIGRATIONS = [
    "ALTER TABLE eval_datasets ADD COLUMN IF NOT EXISTS judge_model TEXT",
]

_datasets_table_ensured = False


async def _ensure_datasets_table_once() -> None:
    await _run_ddl_once(
        _DATASETS_DDL,
        _DATASETS_DDL_MIGRATIONS,
        "_datasets_table_ensured",
        "eval_datasets",
    )


_DATASET_ITEMS_DDL = """
    CREATE TABLE IF NOT EXISTS eval_dataset_items (
        id          SERIAL PRIMARY KEY,
        case_id     TEXT NOT NULL UNIQUE,
        case_data   JSONB NOT NULL,
        judge_model TEXT,
        created_by  TEXT,
        updated_by  TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
"""

_DATASET_ITEMS_DDL_MIGRATIONS = [
    """
    INSERT INTO eval_dataset_items (case_id, case_data, judge_model, created_at, updated_at)
    SELECT COALESCE(NULLIF(TRIM(c->>'id'), ''), gen_random_uuid()::text),
           c, ed.judge_model, ed.created_at, ed.created_at
    FROM eval_datasets ed,
         jsonb_array_elements(ed.dataset->'cases') WITH ORDINALITY AS t(c, ord)
    WHERE NOT EXISTS (SELECT 1 FROM eval_dataset_items LIMIT 1)
    ORDER BY ed.id, t.ord
    """,
]

_dataset_items_table_ensured = False


async def _ensure_dataset_items_table_once() -> None:
    await _run_ddl_once(
        _DATASET_ITEMS_DDL,
        _DATASET_ITEMS_DDL_MIGRATIONS,
        "_dataset_items_table_ensured",
        "eval_dataset_items",
    )


async def _has_postgres_dataset() -> bool:
    """Return True if eval_dataset_items has at least one row."""
    try:
        await _ensure_dataset_items_table_once()
        async with _pg_conn() as conn:
            row = await conn.execute(
                "SELECT 1 FROM eval_dataset_items LIMIT 1",
            )
            return await row.fetchone() is not None
    except Exception as exc:
        log.warning("Could not check Postgres dataset: %s", exc)
        return False


async def _require_eval_files() -> None:
    """Validate that eval can run, then let the eval runner handle all file I/O."""
    from fastapi import HTTPException

    has_pg = await _has_postgres_dataset()
    if not has_pg:
        is_dev = os.environ.get("ENVIRONMENT", "development").lower() == "development"
        config_dir = os.environ.get("CONFIG_PATH", "config/agent")
        eval_cases = Path(f"{config_dir}/evals/lightspeed/eval_cases.yaml")
        if is_dev and eval_cases.exists():
            log.info(
                "Dev mode: no Postgres dataset — eval runner will use eval_cases.yaml from config. "
                "Save cases via the Dataset UI to switch to Postgres-managed evals."
            )
        else:
            config_hint = (
                " A config file (eval_cases.yaml) exists but is ignored in production — "
                "save your dataset via the Dataset UI."
                if eval_cases.exists()
                else ""
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    "No eval dataset saved. Add or import test cases via the Dataset UI "
                    f"before running evaluation.{config_hint}"
                ),
            )


class EvalRecordOut(BaseModel):
    """One row of the `evals` table, as `SELECT *` returns it."""

    eval_status: str
    message: str | None = None
    config_hash: str | None = None
    eval_score: float | None = None
    ls_run_ids: list[str] | None = None
    pass_: int | None = Field(default=None, alias="pass")
    fail: int | None = None
    error: int | None = None
    judge_model: str | None = None
    results_detail: dict[str, Any] | None = None
    force_reeval: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None
    review: list[dict[str, Any]] | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class EvalTriggerOut(BaseModel):
    """The answer to asking for a run."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    eval_status: str
    message: str | None = None
    cached: bool | None = None
    queued: bool | None = None
    config_hash: str | None = None
    forced: bool | None = None


class EvalHistoryRunOut(BaseModel):
    """One past eval run and how it scored."""

    eval_score: float | None = None
    pass_: int | None = Field(default=None, alias="pass")
    fail: int | None = None
    error: int | None = None
    config_hash: str | None = None
    created_at: str | None = None
    completed_at: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class EvalHistoryOut(BaseModel):
    """Past eval runs, newest first."""

    runs: list[EvalHistoryRunOut]
    total: int


class TrendPointOut(BaseModel):
    """One point on an eval trend: when, and the score."""

    completed_at: str
    pass_rate: float | None = None


class OverallPointOut(BaseModel):
    """One point on the overall eval score over time."""

    completed_at: str
    eval_score: float | None = None


class EvalTrendsOut(BaseModel):
    """How eval scores have moved, per metric and overall."""

    metrics: dict[str, list[TrendPointOut]]
    overall: list[OverallPointOut]


class EvalDriftOut(BaseModel):
    """Whether eval scores have drifted since the last baseline."""

    movement: str
    gap: float
    outliers: list[Any]
    needs_attention: bool


class EvalModelOut(BaseModel):
    """One model an eval ran against."""

    model: str
    source: str
    default: bool = False

    model_config = ConfigDict(extra="allow", protected_namespaces=())


class EvalModelsOut(BaseModel):
    """Every model evals may run against."""

    models: list[EvalModelOut]


class EvalDatasetCasesOut(BaseModel):
    """The cases in one eval dataset."""

    cases: list[Any]


class EvalDatasetOut(BaseModel):
    """One eval dataset and what it covers."""

    dataset: EvalDatasetCasesOut
    judge_model: str | None = None
    created_at: str | None = None


class DatasetUpsertedOut(BaseModel):
    """What an upsert changed in a dataset."""

    status: str
    case_count: int


class EvalExportOut(BaseModel):
    """An eval run in a form something else can read."""

    eval_score: float | None = None
    pass_: int | None = Field(default=None, alias="pass")
    fail: int | None = None
    error: int | None = None
    completed_at: str | None = None
    total_evaluations: int
    total_turns: int
    turns: list[dict[str, Any]]
    truncated: bool

    model_config = ConfigDict(populate_by_name=True)


class CleanupOut(BaseModel):
    """What the eval cleanup removed."""

    status: str


@eval_mgmt_router.post(
    "/trigger", response_model=None, responses={200: {"model": EvalTriggerOut}}
)
async def trigger_eval(
    request: Request, _token: str = Depends(_require_developer)
) -> Any:
    """Cache-first eval trigger. Returns cached result or sets in_progress."""
    await _require_eval_files()

    config_hash = _get_config_hash()

    await _ensure_evals_table_once()
    async with _pg_conn() as conn:
        row = await conn.execute(
            "SELECT * FROM evals WHERE config_hash=%s "
            "AND eval_status='completed' AND completed_at > NOW() - INTERVAL '24 hours' "
            "ORDER BY completed_at DESC LIMIT 1",
            (config_hash,),
        )
        existing = await row.fetchone()
        if existing:
            doc = _pg_row_to_dict(existing, row)
            try:
                ds_row = await conn.execute(
                    "SELECT MAX(updated_at) FROM eval_dataset_items",
                )
                ds = await ds_row.fetchone()
                ds_ts = ds[0] if ds else None
                if ds_ts is None:
                    log.info(
                        "eval_dataset_items is empty — bypassing cache to pick up config file"
                    )
                    existing = None
                elif doc.get("completed_at") and ds_ts > doc["completed_at"]:
                    log.info(
                        "Dataset updated after last eval (dataset=%s eval=%s) — bypassing cache",
                        ds_ts.isoformat(),
                        doc["completed_at"],
                    )
                    existing = None
            except Exception as exc:
                log.warning("Could not check dataset recency for cache bypass: %s", exc)

        if existing:
            doc = _pg_row_to_dict(existing, row)
            doc.pop("id", None)
            return {**doc, "cached": True}

    missing_auth = await _check_mcp_auth(request)
    if missing_auth:
        return JSONResponse(
            status_code=403,
            content={
                "message": "Connect required MCP servers before running eval",
                "auth_required": missing_auth,
            },
        )

    record, is_new = await _atomic_set_in_progress(config_hash, force=False)
    if not is_new:
        return {"eval_status": "in_progress", "message": "evaluation already running"}
    return await _queue_eval_run(config_hash, request, record)


@eval_mgmt_router.post(
    "/force-trigger",
    response_model=None,
    responses={200: {"model": EvalTriggerOut}},
)
async def force_trigger_eval(
    request: Request, _token: str = Depends(_require_developer)
) -> Any:
    """Force a fresh eval run, bypassing cache."""
    missing_auth = await _check_mcp_auth(request)
    if missing_auth:
        return JSONResponse(
            status_code=403,
            content={
                "message": "Connect required MCP servers before running eval",
                "auth_required": missing_auth,
            },
        )

    await _require_eval_files()

    config_hash = _get_config_hash()

    record, is_new = await _atomic_set_in_progress(config_hash, force=True)
    if not is_new:
        return {"eval_status": "in_progress", "message": "evaluation already running"}
    return await _queue_eval_run(config_hash, request, record, forced=True)


async def _queue_eval_run(
    config_hash: str,
    request: Request,
    record: dict | None,
    *,
    forced: bool = False,
) -> dict[str, Any]:
    auth_token = request.headers.get("authorization", "")
    from agent.aegra.redis import run_redis

    sub = _extract_sub(request)
    await run_redis(
        _write_eval_redis, sub or "", request.headers.get("x-refresh-token", "")
    )
    row_ts = record.get("created_at") if record else None
    eval_row_id: int | None = record.get("id") if record else None

    error_msg = await _fire_eval_run(config_hash, auth_token, row_ts, eval_row_id)
    if error_msg:
        await _mark_eval_error(config_hash, error_msg, row_ts or datetime.now(UTC))
        raise HTTPException(status_code=503, detail=error_msg)

    result: dict[str, Any] = {
        "eval_status": "in_progress",
        "queued": True,
        "config_hash": config_hash,
    }
    if forced:
        result["forced"] = True
    return result


_EVAL_STALE_TIMEOUT_MINUTES = int(os.environ.get("EVAL_STALE_TIMEOUT_MINUTES", "30"))


@eval_mgmt_router.get("/status", responses={200: {"model": EvalRecordOut}})
async def eval_status(
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Return the latest eval record for this agent."""
    has_pg = await _has_postgres_dataset()
    if not has_pg:
        config_dir = os.environ.get("CONFIG_PATH", "config/agent")
        eval_cases = Path(f"{config_dir}/evals/lightspeed/eval_cases.yaml")
        if not eval_cases.exists():
            return {
                "eval_status": "no_dataset",
                "message": "No eval dataset configured. Add test cases via the Dataset UI before running evaluation.",
            }

    await _ensure_evals_table_once()
    try:
        async with _pg_conn() as conn:
            await conn.execute(
                "UPDATE evals SET eval_status='error', completed_at=NOW(), updated_at=NOW() "
                "WHERE eval_status='in_progress' "
                "AND created_at < NOW() - make_interval(mins => %s)",
                (_EVAL_STALE_TIMEOUT_MINUTES,),
            )
            row = await conn.execute(
                "SELECT * FROM evals ORDER BY created_at DESC LIMIT 1",
            )
            result = await row.fetchone()
            if not result:
                return {"eval_status": "not_started", "message": "no eval runs yet"}
            doc = _pg_row_to_dict(result, row)
            doc.pop("id", None)
            return doc
    except Exception as exc:
        import psycopg

        if isinstance(exc, psycopg.errors.UndefinedTable):
            global _table_ensured
            _table_ensured = False
            log.warning(
                "evals table does not exist yet — no eval results available: %s", exc
            )
            return {
                "eval_status": "no_dataset",
                "message": "No eval results exist yet. Run an evaluation first.",
            }
        raise


_TURN_COLUMNS = (
    "conversation_group_id, turn_id, tag, metric_identifier, "
    "result, score, reason, "
    "judge_llm_input_tokens, judge_llm_output_tokens"
)


@eval_mgmt_router.get("/results", responses={200: {"model": EvalRecordOut}})
async def eval_results(
    request: Request, _token: str = Depends(_require_developer)
) -> dict[str, Any]:
    """Return a completed eval report."""
    from fastapi import HTTPException

    completed_at = request.query_params.get("completed_at")
    await _ensure_evals_table_once()
    try:
        async with _pg_conn() as conn:
            if completed_at:
                row = await conn.execute(
                    "SELECT * FROM evals "
                    "WHERE eval_status='completed' AND completed_at=%s "
                    "LIMIT 1",
                    (completed_at,),
                )
            else:
                row = await conn.execute(
                    "SELECT * FROM evals WHERE eval_status='completed' "
                    "ORDER BY completed_at DESC LIMIT 1",
                )
            result = await row.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="no completed eval results")
            doc = _pg_row_to_dict(result, row)
            doc.pop("id", None)

            rd = doc.get("results_detail") or {}
            if isinstance(rd, str):
                rd = json.loads(rd)
            doc["results_detail"] = rd
            if "turns" not in rd:
                run_ids = doc.get("ls_run_ids") or []
                if run_ids:
                    try:
                        turns_cur = await conn.execute(
                            f"SELECT {_TURN_COLUMNS} "
                            "FROM evaluation_results "
                            "WHERE run_id = ANY(%s) ORDER BY id",
                            (run_ids,),
                        )
                        turn_cols = [d.name for d in turns_cur.description]
                        rd["turns"] = [
                            dict(zip(turn_cols, t)) for t in await turns_cur.fetchall()
                        ]
                    except Exception as turns_exc:
                        log.warning(
                            "Could not fetch turns from evaluation_results: %s",
                            turns_exc,
                        )

            from agent.aegra.eval_annotation import queue_from_turns

            try:
                doc["review"] = queue_from_turns(rd.get("turns") or [])
            except Exception:
                log.debug("Could not build the review queue", exc_info=True)
                doc["review"] = []

            return doc
    except HTTPException:
        raise
    except Exception as exc:
        import psycopg

        if isinstance(exc, psycopg.errors.UndefinedTable):
            global _table_ensured
            _table_ensured = False
            log.warning(
                "evals table does not exist yet — no eval results available: %s", exc
            )
            raise HTTPException(status_code=404, detail="no completed eval results")
        raise


_EXPORT_COLUMNS = (
    "conversation_group_id, turn_id, tag, metric_identifier, "
    "result, score, threshold, reason, "
    "query, response, expected_response, expected_intent, "
    "expected_keywords, expected_tool_calls, tool_calls, contexts, "
    "execution_time, evaluation_latency, agent_latency, "
    "judge_llm_input_tokens, judge_llm_output_tokens"
)

_EXPORT_ROW_LIMIT = settings.EVAL_EXPORT_ROW_LIMIT


@eval_mgmt_router.get("/results/export", responses={200: {"model": EvalExportOut}})
async def export_results(
    request: Request, _token: str = Depends(_require_developer)
) -> dict[str, Any]:
    """Export turn-level results for a completed eval run."""
    completed_at = request.query_params.get("completed_at")
    try:
        req_limit = int(request.query_params.get("limit", _EXPORT_ROW_LIMIT))
    except (ValueError, TypeError):
        req_limit = _EXPORT_ROW_LIMIT
    row_limit = max(1, min(req_limit, _EXPORT_ROW_LIMIT))

    await _ensure_evals_table_once()

    async with _pg_conn() as conn:
        if completed_at:
            row = await conn.execute(
                "SELECT ls_run_ids, eval_score, pass, fail, error, completed_at "
                "FROM evals WHERE eval_status='completed' AND completed_at=%s LIMIT 1",
                (completed_at,),
            )
        else:
            row = await conn.execute(
                "SELECT ls_run_ids, eval_score, pass, fail, error, completed_at "
                "FROM evals WHERE eval_status='completed' "
                "ORDER BY completed_at DESC LIMIT 1",
            )
        eval_row = await row.fetchone()
        if not eval_row:
            raise HTTPException(status_code=404, detail="no completed eval results")

        cols = [d.name for d in row.description]
        eval_doc = dict(zip(cols, eval_row))
        run_ids = eval_doc.get("ls_run_ids") or []

        if not run_ids:
            raise HTTPException(
                status_code=404, detail="no run IDs found for this eval"
            )

        count_cur = await conn.execute(
            "SELECT COUNT(*), "
            "COUNT(DISTINCT (conversation_group_id, turn_id)) "
            "FROM evaluation_results WHERE run_id = ANY(%s)",
            (run_ids,),
        )
        total_available, total_turns = await count_cur.fetchone()

        turns_cur = await conn.execute(
            f"SELECT {_EXPORT_COLUMNS} FROM evaluation_results "
            "WHERE run_id = ANY(%s) ORDER BY id LIMIT %s",
            (run_ids, row_limit),
        )
        turn_cols = [d.name for d in turns_cur.description]
        turns = [dict(zip(turn_cols, t)) for t in await turns_cur.fetchall()]

    return {
        "eval_score": eval_doc.get("eval_score"),
        "pass": eval_doc.get("pass"),
        "fail": eval_doc.get("fail"),
        "error": eval_doc.get("error"),
        "completed_at": (
            eval_doc["completed_at"].isoformat()
            if hasattr(eval_doc.get("completed_at"), "isoformat")
            else str(eval_doc.get("completed_at"))
        ),
        "total_evaluations": total_available,
        "total_turns": total_turns,
        "turns": turns,
        "truncated": total_available > row_limit,
    }


@eval_mgmt_router.get("/history", responses={200: {"model": EvalHistoryOut}})
async def eval_history(
    request: Request, _token: str = Depends(_require_developer)
) -> dict[str, Any]:
    """Return historical completed eval runs (scalars only, no results_detail)."""
    try:
        limit = min(int(request.query_params.get("limit", "20")), 100)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="'limit' must be a positive integer"
        )
    await _ensure_evals_table_once()

    try:
        async with _pg_conn() as conn:
            cur = await conn.execute(
                "SELECT eval_score, pass, fail, error, config_hash, "
                "       created_at, completed_at, "
                "       COUNT(*) OVER() AS total_count "
                "FROM evals "
                "WHERE eval_status='completed' "
                "ORDER BY completed_at DESC LIMIT %s",
                (limit,),
            )
            cols = [d.name for d in cur.description]
            runs = []
            total = 0
            async for row in cur:
                d = dict(zip(cols, row))
                total = d.pop("total_count", 0)
                for k in ("created_at", "completed_at"):
                    if d.get(k) is not None:
                        d[k] = (
                            d[k].isoformat()
                            if hasattr(d[k], "isoformat")
                            else str(d[k])
                        )
                runs.append(d)
    except Exception as exc:
        import psycopg

        if isinstance(exc, psycopg.errors.UndefinedTable):
            global _table_ensured
            _table_ensured = False
            log.warning(
                "evals table does not exist yet — no eval history available: %s", exc
            )
            return {"runs": [], "total": 0}
        raise

    return {"runs": runs, "total": total}


@eval_mgmt_router.get("/trends", responses={200: {"model": EvalTrendsOut}})
async def eval_trends(
    request: Request, _token: str = Depends(_require_developer)
) -> dict[str, Any]:
    """Return per-metric score trends across historical eval runs."""
    try:
        limit = min(int(request.query_params.get("limit", "20")), 100)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="'limit' must be a positive integer"
        )
    await _ensure_evals_table_once()

    try:
        async with _pg_conn() as conn:
            cur = await conn.execute(
                "SELECT results_detail->'summary'->'summary_stats'->'by_metric' as by_metric, "
                "       eval_score, completed_at "
                "FROM evals "
                "WHERE eval_status='completed' "
                "  AND results_detail IS NOT NULL "
                "ORDER BY completed_at DESC LIMIT %s",
                (limit,),
            )

            metrics: dict[str, list[dict]] = {}
            overall: list[dict] = []

            async for row in cur:
                by_metric_raw, eval_score, completed_at = row
                ts = (
                    completed_at.isoformat()
                    if hasattr(completed_at, "isoformat")
                    else str(completed_at)
                )
                overall.append({"completed_at": ts, "eval_score": eval_score})

                by_metric = by_metric_raw if isinstance(by_metric_raw, dict) else {}
                for metric_name, stats in by_metric.items():
                    if metric_name not in metrics:
                        metrics[metric_name] = []
                    metrics[metric_name].append(
                        {
                            "completed_at": ts,
                            "pass_rate": stats.get("pass_rate")
                            if isinstance(stats, dict)
                            else None,
                        }
                    )
    except Exception as exc:
        import psycopg

        if isinstance(exc, psycopg.errors.UndefinedTable):
            global _table_ensured
            _table_ensured = False
            log.warning(
                "evals table does not exist yet — no eval trends available: %s", exc
            )
            return {"metrics": {}, "overall": []}
        raise

    return {"metrics": metrics, "overall": overall}


@eval_mgmt_router.get("/drift", responses={200: {"model": EvalDriftOut}})
async def eval_drift(
    request: Request, _token: str = Depends(_require_developer)
) -> dict[str, Any]:
    """Say whether scores are holding, rising or falling against a baseline."""
    from agent.aegra.eval_drift import summarise_drift

    try:
        baseline = float(request.query_params.get("baseline", "0.8"))
        limit = min(int(request.query_params.get("limit", "20")), 100)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="'baseline' and 'limit' must be numbers"
        )

    await _ensure_evals_table_once()

    try:
        async with _pg_conn() as conn:
            cur = await conn.execute(
                "SELECT id, eval_score, pass, fail, error "
                "FROM evals "
                "WHERE eval_status='completed' AND eval_score IS NOT NULL "
                "ORDER BY completed_at DESC LIMIT %s",
                (limit,),
            )
            rows = await cur.fetchall()
    except Exception as exc:
        import psycopg

        if isinstance(exc, psycopg.errors.UndefinedTable):
            global _table_ensured
            _table_ensured = False
            log.warning("evals table does not exist yet — no drift to report: %s", exc)
            rows = []
        else:
            raise

    try:
        return summarise_drift(rows, baseline=baseline)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _collect_agent_models() -> list[dict[str, Any]]:
    """Read model: from PROMPT.md + all subagent .md frontmatters."""
    import re

    import yaml as _yaml  # noqa: PLC0415

    config_dir = os.environ.get("CONFIG_PATH", "config/agent")
    models: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _parse_model(path: Path, source: str, default: bool = False) -> None:
        if not path.exists():
            return
        try:
            content = path.read_text(encoding="utf-8")
            m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not m:
                return
            fm = _yaml.safe_load(m.group(1)) or {}
            model = str(fm.get("model", "")).strip()
            if model and model not in seen:
                models.append({"model": model, "source": source, "default": default})
                seen.add(model)
        except Exception as exc:
            log.warning("Could not parse model from %s: %s", path, exc)

    _parse_model(Path(f"{config_dir}/PROMPT.md"), "orchestrator", default=True)

    subagents_dir = Path(f"{config_dir}/subagents")
    if subagents_dir.exists():
        for md_file in sorted(subagents_dir.glob("*.md")):
            fm_source = f"subagent:{md_file.stem}"
            _parse_model(md_file, fm_source)

    return models


@eval_mgmt_router.get("/models", responses={200: {"model": EvalModelsOut}})
async def get_eval_models(
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Return available LLM models for evaluation (orchestrator + subagents)."""
    return {"models": _collect_agent_models()}


class DatasetUpsertRequest(BaseModel):
    """Dataset payload sent from the UI."""

    cases: list[dict[str, Any]]
    judge_model: str | None = None


@eval_mgmt_router.post(
    settings.EVAL_DATASET_ROUTE_PREFIX, responses={200: {"model": DatasetUpsertedOut}}
)
async def upsert_dataset(
    body: DatasetUpsertRequest,
    request: Request,
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Upsert the eval dataset for this agent."""
    await _ensure_dataset_items_table_once()
    now = datetime.now(UTC)
    username = _extract_username(request) or ""

    normalized: list[tuple[str, dict]] = []
    seen_ids: dict[str, int] = {}
    for idx, case in enumerate(body.cases):
        raw_id = case.get("id")
        cid = str(raw_id).strip() if raw_id is not None else ""
        if not cid:
            cid = str(uuid.uuid4())
        if cid in seen_ids:
            raise HTTPException(
                status_code=422,
                detail=f"Duplicate case ID {cid!r} at positions {seen_ids[cid]} and {idx}",
            )
        seen_ids[cid] = idx
        normalized.append((cid, case))

    async with _pg_conn() as conn:
        await conn.execute("DELETE FROM eval_dataset_items")
        for cid, case in normalized:
            await conn.execute(
                "INSERT INTO eval_dataset_items "
                "(case_id, case_data, judge_model, created_by, updated_by, created_at, updated_at) "
                "VALUES (%s, %s::jsonb, %s, %s, %s, %s, %s)",
                (
                    str(cid),
                    json.dumps(case),
                    body.judge_model,
                    username,
                    username,
                    now,
                    now,
                ),
            )

    log.info(
        "Dataset upserted: cases=%d judge_model=%s user=%s",
        len(body.cases),
        body.judge_model,
        username,
    )
    return {"status": "ok", "case_count": len(body.cases)}


@eval_mgmt_router.get(
    settings.EVAL_DATASET_ROUTE_PREFIX, responses={200: {"model": EvalDatasetOut}}
)
async def get_dataset(
    _token: str = Depends(_require_developer),
) -> dict[str, Any]:
    """Return the stored eval dataset for this agent."""
    await _ensure_dataset_items_table_once()

    async with _pg_conn() as conn:
        cursor = await conn.execute(
            "SELECT case_data, judge_model, created_at "
            "FROM eval_dataset_items ORDER BY id",
        )
        rows = await cursor.fetchall()

    if not rows:
        return {"dataset": {"cases": []}, "judge_model": None, "created_at": None}

    cases: list[Any] = []
    judge_model = None
    latest_created_at = None
    for case_data, jm, created_at in rows:
        if isinstance(case_data, str):
            case_data = json.loads(case_data)
        cases.append(case_data)
        if jm:
            judge_model = jm
        if created_at and (latest_created_at is None or created_at > latest_created_at):
            latest_created_at = created_at

    return {
        "dataset": {"cases": cases},
        "judge_model": judge_model,
        "created_at": (
            latest_created_at.isoformat()  # type: ignore[union-attr]
            if hasattr(latest_created_at, "isoformat")
            else str(latest_created_at)
            if latest_created_at
            else None
        ),
    }


@eval_mgmt_router.post("/internal/cleanup", responses={200: {"model": CleanupOut}})
async def cleanup_eval_redis(request: Request) -> dict[str, Any]:
    """Delete eval Redis keys when an eval run completes."""
    if not _EVAL_TOKEN_REFRESH_ENABLED:
        return {"status": "disabled"}

    provided = request.headers.get("x-internal-token", "")
    if not _EVAL_INTERNAL_TOKEN or not hmac.compare_digest(
        provided.encode(), _EVAL_INTERNAL_TOKEN.encode()
    ):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="invalid internal token")

    try:
        from agent.aegra.redis import cache_delete, cache_get, run_redis

        sub = await run_redis(cache_get, "eval:trigger_sub")
        await run_redis(cache_delete, "eval:trigger_sub")
        if sub:
            await run_redis(cache_delete, f"eval:active:{sub}")
            await run_redis(cache_delete, f"eval:access:{sub}")
            await run_redis(cache_delete, f"eval:refresh:{sub}")
        log.info("eval_redis_cleanup keys_deleted=%d", 4 if sub else 1)
    except Exception as exc:
        log.warning("eval_redis_cleanup failed (TTL will handle): %s", exc)

    return {"status": "ok"}


class DeclaredCheckOut(BaseModel):
    """One check as the config tree declares it."""

    name: str
    group: str
    decides: str
    kind: str = "judged"
    corpus: str = ""
    judge: str = ""
    dataset: str = ""
    cases: list[int] = []
    source: str = ""


class CheckProblemOut(BaseModel):
    """A file that would not load, and why."""

    where: str
    what: str


class DeclaredChecksOut(BaseModel):
    """Every declared check, grouped, with whatever would not load."""

    groups: list[str]
    checks: list[DeclaredCheckOut]
    problems: list[CheckProblemOut]
    counts: dict[str, int]


class CheckUsageRowOut(BaseModel):
    """How often one check has been run."""

    name: str
    runs: int


class CheckUsageOut(BaseModel):
    """Run counts, least-used first."""

    rows: list[CheckUsageRowOut]
    unused: list[str]


@eval_mgmt_router.get("/checks", responses={200: {"model": DeclaredChecksOut}})
async def list_declared_checks() -> dict[str, Any]:
    """The checks this deployment declares, grouped."""
    from agent.src.agent.config.paths import config_root
    from agent.src.evals.declared import declared_registry

    registry, problems = declared_registry(config_root())
    groups = registry.groups()
    return {
        "groups": list(groups),
        "checks": [
            {
                "name": c.name,
                "group": c.group,
                "decides": c.decides,
                "kind": c.kind,
                "corpus": c.corpus,
                "judge": c.judge,
                "dataset": c.dataset,
                "cases": list(c.cases),
                "source": c.source,
            }
            for group in groups
            for c in registry.in_group(group)
        ],
        "problems": problems,
        "counts": {group: len(registry.in_group(group)) for group in groups},
    }


@eval_mgmt_router.get("/checks/usage", responses={200: {"model": CheckUsageOut}})
async def declared_check_usage() -> dict[str, Any]:
    """Run counts per check, least used first."""
    from agent.src.agent.config.paths import config_root
    from agent.src.evals import usage as usage_counts
    from agent.src.evals.declared import declared_registry

    registry, _ = declared_registry(config_root())
    usage = usage_counts.applied_to(registry)
    return {
        "rows": sorted(
            ({"name": n, "runs": r} for n, r in usage.items()),
            key=lambda row: (row["runs"], row["name"]),
        ),
        "unused": sorted(name for name, runs in usage.items() if runs == 0),
    }
