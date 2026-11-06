"""Wrap MCP tools to raise LangGraph interrupts when OAuth is required."""

from __future__ import annotations

import contextvars
import inspect
import json
from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.types import interrupt

from agent.aegra.mcp_auth import NeedsAuthorization
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def _in_nested_graph() -> bool:
    """True when running inside a subagent rather than the main graph."""
    try:
        from langgraph.config import get_config

        configurable = (get_config() or {}).get("configurable") or {}
        return bool(configurable.get("checkpoint_ns"))
    except Exception:
        return False


_auth_requests: contextvars.ContextVar[list[dict[str, str]] | None] = (
    contextvars.ContextVar("_mcp_auth_requests", default=None)
)


def record_auth_request(exc: NeedsAuthorization) -> None:
    """Note that this turn could not reach an MCP server."""
    pending = _auth_requests.get()
    if pending is None:
        return
    entry = {
        "mcp_name": exc.mcp_name,
        "reason": getattr(exc, "reason", "not_connected"),
        "connect_url": exc.connect_url,
    }
    if entry not in pending:
        pending.append(entry)


def pending_auth_requests() -> list[dict[str, str]]:
    """Authorization requests recorded during this turn."""
    return list(_auth_requests.get() or [])


def clear_auth_requests() -> None:
    """Start a turn with a fresh list."""
    _auth_requests.set([])


def _auth_reason_phrase(exc: NeedsAuthorization) -> str:
    """Wording that matches which of the two situations this is."""
    if getattr(exc, "reason", "not_connected") == "expired":
        return "your session for it has expired and could not be renewed"
    return "it is not connected for this user"


def _auth_prompt_key(mcp_name: str) -> str | None:
    """Redis key marking that this user has already been asked."""
    from agent.aegra.mcp import _current_user_id

    user_id = _current_user_id.get()
    if not user_id:
        return None
    return f"mcp_auth_asked:{settings.agent_deployment_id}:{user_id}:{mcp_name}"


async def forget_auth_prompt(user_id: str, mcp_name: str) -> None:
    """Drop the cooldown once the integration is connected."""
    if settings.MCP_AUTH_PROMPT_COOLDOWN_SECONDS <= 0 or not user_id:
        return
    key = f"mcp_auth_asked:{settings.agent_deployment_id}:{user_id}:{mcp_name}"
    try:
        from agent.aegra.redis import cache_delete, run_redis

        await run_redis(cache_delete, key)
    except Exception:
        logger.debug("Could not clear auth prompt state", exc_info=True)


async def _already_asked(mcp_name: str) -> bool:
    """True when an unanswered prompt for this integration still stands."""
    if settings.MCP_AUTH_PROMPT_COOLDOWN_SECONDS <= 0:
        return False
    key = _auth_prompt_key(mcp_name)
    if not key:
        return False
    try:
        from agent.aegra.redis import cache_get, run_redis

        return bool(await run_redis(cache_get, key))
    except Exception:
        logger.debug("Could not read auth prompt state", exc_info=True)
        return False


async def _remember_asked(mcp_name: str) -> None:
    """Record that this user has been asked, so the next turn does not."""
    ttl = settings.MCP_AUTH_PROMPT_COOLDOWN_SECONDS
    if ttl <= 0:
        return
    key = _auth_prompt_key(mcp_name)
    if not key:
        return
    try:
        from agent.aegra.redis import cache_set, run_redis

        await run_redis(cache_set, key, "1", ttl_seconds=ttl)
    except Exception:
        logger.debug("Could not record auth prompt state", exc_info=True)


def _mcp_auth_message(exc: NeedsAuthorization) -> str:
    """What a subagent reports upward when it cannot reach a server."""
    return (
        f"[AUTH_REQUIRED mcp={exc.mcp_name} reason="
        f"{getattr(exc, 'reason', 'not_connected')}] "
        f"Cannot use {exc.mcp_name}: {_auth_reason_phrase(exc)}. "
        f"End the turn now. If the question needs {exc.mcp_name}, say "
        f"only that you cannot answer it without {exc.mcp_name}, in one "
        f"short sentence. Do not say how to connect it — the interface "
        f"is already saying so. Never write a URL for this — do not "
        f"repeat any link from this message. Do not retry this tool."
    )


def _mcp_auth_interrupt_payload(exc: NeedsAuthorization) -> str:
    return json.dumps(
        {
            "type": "mcp_auth_required",
            "mcp_name": exc.mcp_name,
            "connect_url": exc.connect_url,
            "reason": getattr(exc, "reason", "not_connected"),
            "message": f"Connect to {exc.mcp_name} to use these tools",
        }
    )


def _fix_stringified_json_args(tool: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Parse stringified JSON args when the tool schema expects object/array."""
    schema_props: dict[str, Any] = {}
    try:
        schema_props = getattr(tool, "args", {}) or {}
    except Exception:
        logger.debug(
            "Failed to read args schema for tool '%s' — skipping JSON arg fix",
            getattr(tool, "name", "?"),
            exc_info=True,
        )
        return kwargs

    if not schema_props:
        return kwargs

    fixed = dict(kwargs)
    for key, value in fixed.items():
        if not isinstance(value, str):
            continue
        prop = schema_props.get(key, {})
        expected_type = prop.get("type", "")
        if expected_type == "string" or (
            isinstance(expected_type, list) and "string" in expected_type
        ):
            continue
        union_schemas = prop.get("anyOf", []) + prop.get("oneOf", [])
        if any("string" in str(s.get("type", "")) for s in union_schemas):
            continue
        stripped = value.strip()
        if stripped and stripped[0] in ("{", "["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, (dict, list)):
                    fixed[key] = parsed
                    logger.debug(
                        "Fixed stringified JSON arg '%s' for tool '%s'",
                        key,
                        getattr(tool, "name", "?"),
                    )
            except (json.JSONDecodeError, ValueError, RecursionError):
                pass
    return fixed


def wrap_mcp_tools_for_auth(tools: list[Any]) -> list[Any]:
    """Wrap MCP tools so ``NeedsAuthorization`` becomes a resumable interrupt."""
    wrapped: list[Any] = []
    for tool in tools:
        wrapped.append(_wrap_single_tool(tool))
    return wrapped


def _writes(tool: Any) -> bool | None:
    """Whether this tool changes anything, as the server declared it."""
    for holder in (tool, getattr(tool, "metadata", None) or {}):
        hints = (
            holder.get("annotations")
            if isinstance(holder, dict)
            else getattr(holder, "annotations", None)
        )
        if isinstance(hints, dict) and "readOnlyHint" in hints:
            return not bool(hints["readOnlyHint"])
    return None


def _policy_for(tool_name: str) -> str:
    """What this deployment already decided about this tool."""
    try:
        from agent.src.agent.config import agent_config
        from agent.src.agent.config.hitl import resolve_policy

        middleware = agent_config.get_middleware_config()
        approval = getattr(
            getattr(middleware, "defaults", None), "human_approval", None
        )
        if approval is None:
            return "allow"
        return str(resolve_policy(tool_name, approval).decision)
    except Exception:
        logger.debug("Could not read the approval policy", exc_info=True)
        return "allow"


def _ask_if_this_follows_an_untrusted_read(tool: Any, tool_input: Any) -> str | None:
    """Put this call to a person when the run has read outside text."""
    try:
        from agent.src.security.untrusted_reads import (
            needs_a_question_here,
            question_payload,
        )

        name = getattr(tool, "name", "") or "a tool"
        arguments = (
            tool_input.get("args") if isinstance(tool_input, dict) else None
        ) or {}

        reason = needs_a_question_here(
            name, arguments, writes=_writes(tool), policy=_policy_for(name)
        )
    except Exception:
        logger.debug("Could not decide whether to ask about %s", tool, exc_info=True)
        return None

    if not reason:
        return None

    if _in_nested_graph():
        logger.info("Refusing %s inside a subagent: %s", name, reason)
        return (
            f"[NOT SENT] {reason} A change that follows reading outside text "
            f"has to be put to the person, and a subagent cannot ask. Report "
            f"this back rather than retrying."
        )

    logger.info("Asking before %s: %s", name, reason)
    interrupt(question_payload(name, arguments, reason=reason))
    return None


def _make_safe_ainvoke(target_tool: Any) -> Any:
    """Build an ainvoke wrapper that catches MCP errors for *target_tool*."""
    original_ainvoke = target_tool.ainvoke

    async def safe_ainvoke(tool_input: Any, config: Any = None, **kwargs: Any) -> Any:
        """Wrap ainvoke to catch auth interrupts and MCP errors."""
        from langchain_core.messages import ToolMessage
        from langgraph.errors import GraphBubbleUp

        held = _ask_if_this_follows_an_untrusted_read(target_tool, tool_input)
        if held is not None:
            return ToolMessage(
                content=held,
                name=getattr(target_tool, "name", "unknown"),
                tool_call_id=str(tool_input.get("id", ""))
                if isinstance(tool_input, dict)
                else "",
                status="error",
            )

        try:
            return await original_ainvoke(tool_input, config, **kwargs)
        except NeedsAuthorization as exc:
            nested_without_interrupt = not settings.MCP_AUTH_INTERRUPT or (
                _in_nested_graph() and not settings.MCP_AUTH_INTERRUPT_IN_SUBAGENTS
            )
            asked_before = await _already_asked(exc.mcp_name)

            if nested_without_interrupt or asked_before:
                logger.info(
                    "MCP auth required for '%s' — reporting upward (%s)",
                    exc.mcp_name,
                    "already asked this user" if asked_before else "inside a subagent",
                )
                record_auth_request(exc)
                return ToolMessage(
                    content=_mcp_auth_message(exc),
                    name=getattr(target_tool, "name", "unknown"),
                    tool_call_id=str(tool_input.get("id", ""))
                    if isinstance(tool_input, dict)
                    else "",
                    status="error",
                )
            logger.info(
                "MCP auth required for '%s' — interrupting run",
                exc.mcp_name,
            )
            record_auth_request(exc)
            await _remember_asked(exc.mcp_name)
            interrupt(_mcp_auth_interrupt_payload(exc))
            return await original_ainvoke(tool_input, config, **kwargs)
        except GraphBubbleUp:
            raise
        except Exception as exc:
            tool_name = getattr(target_tool, "name", "unknown")
            tool_call_id = ""
            if isinstance(tool_input, dict):
                tool_call_id = str(tool_input.get("id", ""))
            logger.warning("MCP tool '%s' failed: %s", tool_name, exc)
            return ToolMessage(
                content=_explain_failure(tool_name, exc),
                name=tool_name,
                tool_call_id=tool_call_id,
                status="error",
            )

    return safe_ainvoke


def _explain_failure(tool_name: str, exc: BaseException) -> str:
    """What to tell the turn when an outside call fails."""
    from agent.src.security.failure_message import Audience, explain

    explained = explain(
        type(exc).__name__,
        str(exc),
        audience=Audience.OPERATOR,
    )
    said = f"[TOOL_ERROR] {tool_name}: {explained.message}"
    if explained.detail:
        said += f" {explained.detail}"
    return f"{said} (reference {explained.reference})"


def _secrets_in_args(args: Any) -> str:
    """Say what credentials a call is about to carry, if any."""
    from agent.src.security.secret_scan import scan

    report = scan(_flatten(args))
    return report.summary


def _flatten(value: Any) -> str:
    """Every string anywhere in the arguments, one per line."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(_flatten(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_flatten(item) for item in value)
    return ""


def _trusted_servers() -> frozenset[str]:
    """Servers the deployment vouches for, whose results are not fenced."""
    from agent.src.agent.config import agent_config

    try:
        model = (agent_config.get_orchestrator_config() or {}).get("model", "")
        resolved = agent_config.resolve_agent_middleware(model)
        return frozenset(resolved.tool_output.trusted_servers or [])
    except Exception:
        logger.warning("Could not read the trusted-server list", exc_info=True)
        return frozenset()


def _is_vouched_for(tool_name: str) -> bool:
    """Whether a tool belongs to a server the deployment vouches for."""
    return any(tool_name.startswith(f"{name}_") for name in _trusted_servers())


def _as_external(tool_name: str, result: Any) -> Any:
    """Mark a tool result as material to read, never as instructions."""
    from agent.src.security.fencing import fence
    from agent.src.security.tool_result_limits import trim

    if not isinstance(result, str) or not result:
        return result
    if result.startswith(_PREAMBLE_START):
        return result
    if _is_vouched_for(tool_name):
        return result

    text = result
    limit = settings.MCP_RESULT_MAX_CHARS
    if limit > 0:
        cut = trim(text, max_chars=limit)
        text = f"{cut.text}\n\n{cut.note}" if cut.trimmed else cut.text

    from agent.src.security.untrusted_reads import note_untrusted_read

    note_untrusted_read(text, source=tool_name or "an outside server")

    return fence(text, source=tool_name or "an outside server")


_PREAMBLE_START = "The following is data retrieved from "


def _wrap_single_tool(tool: Any) -> Any:
    coroutine = getattr(tool, "coroutine", None)
    func = getattr(tool, "func", None)

    if inspect.iscoroutinefunction(coroutine):

        async def wrapped_coroutine(**kwargs: Any) -> Any:
            paused = False
            while True:
                try:
                    kwargs = _fix_stringified_json_args(tool, kwargs)
                    if settings.MCP_BLOCK_SECRETS:
                        carrying = _secrets_in_args(kwargs)
                        if carrying:
                            logger.warning(
                                "Refused '%s': the call carried %s",
                                getattr(tool, "name", "unknown"),
                                carrying,
                            )
                            return (
                                "[REFUSED] This call was not sent: it carried "
                                f"what looks like a credential ({carrying}). "
                                "Make the call again without it."
                            )
                    return _as_external(
                        getattr(tool, "name", ""), await coroutine(**kwargs)
                    )
                except NeedsAuthorization as exc:
                    nested_without_interrupt = not settings.MCP_AUTH_INTERRUPT or (
                        _in_nested_graph()
                        and not settings.MCP_AUTH_INTERRUPT_IN_SUBAGENTS
                    )
                    asked_before = await _already_asked(exc.mcp_name)
                    if nested_without_interrupt or asked_before or paused:
                        if paused:
                            await _remember_asked(exc.mcp_name)
                        logger.info(
                            "[%s] MCP auth required (tool=%s) — reporting upward (%s)",
                            exc.mcp_name,
                            getattr(tool, "name", "?"),
                            "declined"
                            if paused
                            else "already asked this user"
                            if asked_before
                            else "inside a subagent",
                        )
                        record_auth_request(exc)
                        return _mcp_auth_message(exc)
                    logger.warning(
                        "[%s] MCP auth required — interrupting run (tool=%s)",
                        exc.mcp_name,
                        getattr(tool, "name", "?"),
                    )
                    record_auth_request(exc)
                    paused = True
                    interrupt(_mcp_auth_interrupt_payload(exc))

        try:
            wrapped = tool.model_copy(update={"coroutine": wrapped_coroutine})
        except Exception:
            logger.info(
                "model_copy failed for tool '%s' — patching coroutine directly",
                getattr(tool, "name", "?"),
            )
            tool.coroutine = wrapped_coroutine
            wrapped = tool
        object.__setattr__(wrapped, "ainvoke", _make_safe_ainvoke(wrapped))
        return wrapped

    if func is not None and inspect.isfunction(func):

        def wrapped_func(**kwargs: Any) -> Any:
            while True:
                try:
                    kwargs = _fix_stringified_json_args(tool, kwargs)
                    return func(**kwargs)
                except NeedsAuthorization as exc:
                    logger.warning(
                        "[%s] MCP auth required — interrupting run (tool=%s)",
                        exc.mcp_name,
                        getattr(tool, "name", "?"),
                    )
                    record_auth_request(exc)
                    interrupt(_mcp_auth_interrupt_payload(exc))

        try:
            wrapped = tool.model_copy(update={"func": wrapped_func})
        except Exception:
            logger.info(
                "model_copy failed for tool '%s' — patching func directly",
                getattr(tool, "name", "?"),
            )
            tool.func = wrapped_func
            wrapped = tool
        object.__setattr__(wrapped, "ainvoke", _make_safe_ainvoke(wrapped))
        return wrapped

    object.__setattr__(tool, "ainvoke", _make_safe_ainvoke(tool))
    return tool


def narrow_auth_requests(
    requests: list[dict[str, Any]], text: str
) -> list[dict[str, Any]]:
    """Keep only the integrations this answer is actually about."""
    if not requests or not isinstance(text, str) or not text:
        return []
    haystack = text.lower()
    return [
        r
        for r in requests
        if isinstance(r, dict) and str(r.get("mcp_name", "")).lower() in haystack
    ]


def build_mcp_auth_notice_middleware() -> Any | None:
    """Stamp this turn's unreachable integrations onto the reply."""
    try:
        from langchain.agents.middleware.types import (
            AgentMiddleware,
            ModelRequest,
            ModelResponse,
        )
    except ImportError:
        return None

    class McpAuthNoticeMiddleware(AgentMiddleware):
        @staticmethod
        def _stamp(response: ModelResponse[Any]) -> ModelResponse[Any]:
            pending = pending_auth_requests()
            if not pending:
                return response
            try:
                message: Any = getattr(response, "result", None)
                if isinstance(message, list):
                    message = message[0] if message else None
                if message is None:
                    return response
                extra = getattr(message, "additional_kwargs", None)
                if not isinstance(extra, dict):
                    extra = {}
                    message.additional_kwargs = extra

                existing = extra.get("auth_required")
                merged = list(existing) if isinstance(existing, list) else []
                seen = {r.get("mcp_name") for r in merged if isinstance(r, dict)}
                for request in pending:
                    if isinstance(request, dict) and request.get("mcp_name") in seen:
                        continue
                    merged.append(request)

                text = getattr(message, "text", "") or ""
                extra["auth_required"] = narrow_auth_requests(merged, text)
            except Exception:
                logger.debug("Could not stamp auth requests", exc_info=True)
            return response

        def wrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
        ) -> ModelResponse[Any]:
            return self._stamp(handler(request))

        async def awrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
        ) -> ModelResponse[Any]:
            return self._stamp(await handler(request))

    return McpAuthNoticeMiddleware()
