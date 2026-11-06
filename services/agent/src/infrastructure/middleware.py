"""Middleware builder for deepagents integration."""

from __future__ import annotations

import contextvars
import importlib
import re
import time
from collections.abc import Awaitable, Callable, Iterable
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from agent.src.agent.config.middleware import ResolvedMiddlewareConfig
from agent.src.infrastructure.extensions import declared_extension
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger(log_level=settings.PYTHON_LOG_LEVEL)

_current_user_info: contextvars.ContextVar[dict[str, str] | None] = (
    contextvars.ContextVar("_current_user_info", default=None)
)

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")
_DELIMITER_RE = re.compile(r"[<>\[\]]")


def _sanitize_identity_value(value: str) -> str:
    """Strip control characters and delimiter characters from an identity value."""
    value = _CONTROL_CHAR_RE.sub("", value)
    value = _DELIMITER_RE.sub("", value)
    return value.strip()


def set_user_info(
    *,
    user_id: str | None = None,
    display_name: str | None = None,
    email: str | None = None,
) -> None:
    """Store the current user's identity fields for system-prompt injection."""
    raw = {"user_id": user_id, "display_name": display_name, "email": email}
    info = {k: _sanitize_identity_value(v) for k, v in raw.items() if v}
    _current_user_info.set(info or None)


def get_current_datetime() -> str:
    """Get the current date and time (UTC), rounded for cache stability."""
    from agent.src.settings import settings

    now = datetime.now(timezone.utc)
    step = max(1, settings.DATETIME_PROMPT_GRANULARITY_SECONDS)
    if step > 1:
        epoch = int(now.timestamp()) // step * step
        now = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return now.strftime("%B %d, %Y, %H:%M:%S UTC")


def build_audit_middleware(
    *,
    mcp_tool_names: frozenset[str] | None = None,
    subagent: str | None = None,
    agent: str | None = None,
) -> Any | None:
    """Return AuditMiddleware when platform audit is enabled, else None."""
    from agent.src.audit.config import is_audit_enabled

    if not is_audit_enabled():
        return None

    from agent.src.audit.middleware import AuditMiddleware

    return AuditMiddleware(
        mcp_tool_names=mcp_tool_names or frozenset(),
        subagent=subagent,
        agent=agent,
    )


def _mcp_tool_names_from_tools(tools: list[Any]) -> frozenset[str]:
    return frozenset(getattr(t, "name", "") for t in tools if getattr(t, "name", None))


def build_opa_middleware() -> Any | None:
    """Return OPAMiddleware when OPA authorization is enabled, else None."""
    from agent.src.opa.config import is_opa_enabled

    if not is_opa_enabled():
        return None

    from agent.src.opa.middleware import OPAMiddleware

    return OPAMiddleware()


def _agent_config_block() -> str:
    """One static line per fact the agent cannot otherwise know."""
    from agent.src.agent.config import agent_config

    def _name_of(raw: Any) -> str:
        if isinstance(raw, dict):
            return str(raw.get("name") or "").strip()
        return str(raw or "").strip()

    lines: list[str] = []
    try:
        orchestrator = agent_config.get_orchestrator_config() or {}
    except Exception:
        logger.debug("Could not read the orchestrator config", exc_info=True)
        return ""

    model = _name_of(orchestrator.get("model"))
    if model:
        lines.append(f"  model: {model}")

    try:
        subagents = agent_config.get_all_subagent_configs() or {}
    except Exception:
        logger.debug("Could not read subagent configs", exc_info=True)
        subagents = {}
    odd = sorted(
        f"{n}: {_name_of(c.get('model'))}"
        for n, c in subagents.items()
        if _name_of(c.get("model")) and _name_of(c.get("model")) != model
    )
    if odd:
        lines.append(f"  subagent models (where they differ): {', '.join(odd)}")

    if not lines:
        return ""
    return (
        "<your-configuration>\n" + "\n".join(lines) + "\n</your-configuration>\n"
        "Read from this deployment's own config. When asked which "
        "model you are, answer from here — not from recollection, "
        "which names the model you saw most in training rather than "
        "the one serving you."
    )


def build_agent_config_middleware() -> Any | None:
    """Tell the agent what it is: model, subagents, skills, servers."""
    try:
        from langchain.agents.middleware.types import (
            AgentMiddleware,
            ModelRequest,
            ModelResponse,
        )
    except ImportError:
        return None

    block = _agent_config_block()
    if not block:
        return None

    class AgentConfigMiddleware(AgentMiddleware):
        def _inject(self, request: ModelRequest[Any]) -> ModelRequest[Any]:
            from deepagents.middleware.subagents import append_to_system_message

            return request.override(
                system_message=append_to_system_message(request.system_message, block),
            )

        def wrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
        ) -> ModelResponse[Any]:
            return handler(self._inject(request))

        async def awrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
        ) -> ModelResponse[Any]:
            return await handler(self._inject(request))

    return AgentConfigMiddleware()


_IDENTITY_MARKER = re.compile(r"<\s*/?\s*authenticated-user\s*>", re.IGNORECASE)


def identity_block(info: Any) -> str:
    """Who the agent is talking to, as the model should read it."""
    if not isinstance(info, dict) or not info:
        return ""

    def safe(value: Any) -> str:
        return _IDENTITY_MARKER.sub(
            lambda m: m.group(0).replace("<", "(").replace(">", ")"), str(value)
        )

    parts = [f"  {safe(key)}: {safe(value)}" for key, value in info.items()]
    return "<authenticated-user>\n" + "\n".join(parts) + "\n</authenticated-user>"


def build_user_identity_middleware() -> Any | None:
    """Build middleware that injects the current user's identity into the system prompt."""
    try:
        from langchain.agents.middleware.types import (
            AgentMiddleware,
            ModelRequest,
            ModelResponse,
        )
    except ImportError:
        return None

    class UserIdentityMiddleware(AgentMiddleware):
        def _inject_identity(self, request: ModelRequest[Any]) -> ModelRequest[Any]:
            info = _current_user_info.get()
            if not info:
                return request
            from deepagents.middleware.subagents import append_to_system_message

            block = identity_block(info)
            if not block:
                return request

            logger.info(
                "UserIdentityMiddleware: injected user identity into system prompt"
            )
            return request.override(
                system_message=append_to_system_message(request.system_message, block),
            )

        def wrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
        ) -> ModelResponse[Any]:
            return handler(self._inject_identity(request))

        async def awrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
        ) -> ModelResponse[Any]:
            return await handler(self._inject_identity(request))

    return UserIdentityMiddleware()


def build_current_datetime_middleware() -> Any | None:
    """Build middleware that injects the current date and time (UTC) into the system prompt."""
    try:
        from langchain.agents.middleware.types import (
            AgentMiddleware,
            ModelRequest,
            ModelResponse,
        )
    except ImportError:
        return None

    class CurrentDatetimeMiddleware(AgentMiddleware):
        def _inject_current_datetime(
            self, request: ModelRequest[Any]
        ) -> ModelRequest[Any]:
            from deepagents.middleware.subagents import append_to_system_message

            current_datetime = get_current_datetime()
            current_datetime_block = (
                "<current-datetime>\n" + current_datetime + "\n</current-datetime>"
            )

            return request.override(
                system_message=append_to_system_message(
                    request.system_message, current_datetime_block
                ),
            )

        def wrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
        ) -> ModelResponse[Any]:
            return handler(self._inject_current_datetime(request))

        async def awrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
        ) -> ModelResponse[Any]:
            return await handler(self._inject_current_datetime(request))

    return CurrentDatetimeMiddleware()


def build_prompt_size_middleware() -> Any | None:
    """Log what each model call actually sends, split by component."""
    if not settings.LOG_PROMPT_SIZE:
        return None

    try:
        from langchain.agents.middleware.types import (
            AgentMiddleware,
            ModelRequest,
            ModelResponse,
        )
    except ImportError:
        return None

    class PromptSizeMiddleware(AgentMiddleware):
        @staticmethod
        def _report(request: ModelRequest[Any]) -> None:
            try:
                system = request.system_message or ""
                system_chars = len(str(system))

                messages = getattr(request, "messages", None) or []
                message_chars = sum(
                    len(str(getattr(m, "content", m))) for m in messages
                )

                tools = getattr(request, "tools", None) or []
                tool_chars = 0
                for tool in tools:
                    tool_chars += len(str(getattr(tool, "description", "") or ""))
                    schema = getattr(tool, "args_schema", None)
                    if schema is not None:
                        tool_chars += len(str(schema))

                total = system_chars + message_chars + tool_chars
                logger.info(
                    "prompt_size",
                    approx_tokens=total // 4,
                    system_chars=system_chars,
                    message_chars=message_chars,
                    tool_chars=tool_chars,
                    tools=len(tools),
                    messages=len(messages),
                )
            except Exception:
                logger.debug("Could not measure prompt size", exc_info=True)

        def wrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
        ) -> ModelResponse[Any]:
            self._report(request)
            started = time.monotonic()
            try:
                return handler(request)
            finally:
                _log_model_call(time.monotonic() - started)

        async def awrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
        ) -> ModelResponse[Any]:
            self._report(request)
            started = time.monotonic()
            try:
                return await handler(request)
            finally:
                _log_model_call(time.monotonic() - started)

    return PromptSizeMiddleware()


def _log_model_call(seconds: float) -> None:
    """Time spent inside the model call itself."""
    logger.info("model_call", seconds=round(seconds, 3))


def _build_gemini_safety_log_middleware() -> Any | None:
    """Build middleware that logs and replaces Gemini safety-blocked empty responses."""
    try:
        from langchain.agents.middleware import AgentMiddleware
    except ImportError:
        return None

    _SAFETY_FINISH_REASONS = frozenset(
        {
            "SAFETY",
            "RECITATION",
            "BLOCKLIST",
            "PROHIBITED_CONTENT",
            "IMAGE_SAFETY",
            "SPII",
            "content_filter",
            "refusal",
        }
    )
    _PROMPT_BLOCK_REASONS = frozenset(
        {
            "SAFETY",
            "BLOCKLIST",
            "PROHIBITED_CONTENT",
            "IMAGE_SAFETY",
            "JAILBREAK",
            "MODEL_ARMOR",
            "OTHER",
        }
    )
    _REFUSAL = (
        "I'm unable to respond to that request as it was flagged by the "
        "content safety filter. Please rephrase your message."
    )

    class GeminiSafetyLogMiddleware(AgentMiddleware):
        """Detect Gemini safety filter blocks and log them."""

        def after_model(self, state: Any, runtime: Any) -> Any:
            return self._check_and_replace(state)

        async def aafter_model(self, state: Any, runtime: Any) -> Any:
            return self._check_and_replace(state)

        def _check_and_replace(self, state: Any) -> Any:
            from langchain_core.messages import AIMessage

            msgs = state.get("messages", []) if isinstance(state, dict) else []
            if not msgs:
                return None
            last = msgs[-1]
            if not isinstance(last, AIMessage):
                return None
            if last.content or last.tool_calls:
                return None
            meta = getattr(last, "response_metadata", {}) or {}

            reason = meta.get("finish_reason", meta.get("stop_reason", ""))
            if reason in _SAFETY_FINISH_REASONS:
                logger.warning(
                    "Gemini safety filter blocked response: "
                    "finish_reason=%s, model=%s, safety_ratings=%s",
                    reason,
                    meta.get("model_name", "unknown"),
                    meta.get("safety_ratings", []),
                )
                msgs[-1] = AIMessage(content=_REFUSAL, id=last.id)
                return {"messages": msgs}

            prompt_feedback = meta.get("prompt_feedback") or {}
            block_reason = prompt_feedback.get("block_reason", "")
            if isinstance(block_reason, int):
                block_reason = ""
            if block_reason in _PROMPT_BLOCK_REASONS:
                logger.warning(
                    "Gemini prompt-level block: block_reason=%s, safety_ratings=%s",
                    block_reason,
                    prompt_feedback.get("safety_ratings", []),
                )
                msgs[-1] = AIMessage(content=_REFUSAL, id=last.id)
                return {"messages": msgs}

            return None

    return GeminiSafetyLogMiddleware()


_NOTHING_TO_ANSWER = (
    "There was no message to answer. Send something and I'll pick it up."
)


def _has_something_to_say(message: Any) -> bool:
    """Whether this message carries anything the model can read."""
    if getattr(message, "tool_calls", None):
        return True

    content = getattr(message, "content", None)
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return bool(content)
    return content is not None


def build_fresh_run_middleware() -> Any | None:
    """Forget what the last run read, before this one starts."""
    try:
        from langchain.agents.middleware import AgentMiddleware
    except ImportError:
        return None

    from agent.src.security.untrusted_reads import forget_reads

    class FreshRunMiddleware(AgentMiddleware):
        def before_agent(self, state: Any, runtime: Any = None) -> None:
            forget_reads()
            return None

        async def abefore_agent(self, state: Any, runtime: Any = None) -> None:
            forget_reads()
            return None

    return FreshRunMiddleware()


def build_nothing_to_send_middleware() -> Any | None:
    """Stop a turn that has nothing in it before it reaches the provider."""
    try:
        from langchain.agents.middleware.types import (
            AgentMiddleware,
            ModelRequest,
            ModelResponse,
        )
    except ImportError:
        return None

    def _empty(request: Any) -> bool:
        messages = getattr(request, "messages", None)
        if messages is None:
            return False
        return not any(_has_something_to_say(message) for message in messages)

    def _refuse() -> ModelResponse[Any]:
        from langchain_core.messages import AIMessage

        logger.warning("Refusing a turn with no message in it")
        return ModelResponse(result=[AIMessage(content=_NOTHING_TO_ANSWER)])

    class NothingToSendMiddleware(AgentMiddleware):
        def wrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
        ) -> ModelResponse[Any]:
            if _empty(request):
                return _refuse()
            return handler(request)

        async def awrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
        ) -> ModelResponse[Any]:
            if _empty(request):
                return _refuse()
            return await handler(request)

    return NothingToSendMiddleware()


def _build_image_sanitize_middleware() -> Any | None:
    """Build middleware that strips markdown image tags from user input and model responses."""
    try:
        from langchain.agents.middleware import AgentMiddleware
    except ImportError:
        return None

    import re

    _IMG_INLINE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
    _IMG_REF = re.compile(r"!\[([^\]]*)\]\[([^\]]+)\]")
    _REF_DEF = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s+\S+[^\n]*$", re.MULTILINE)

    def _strip_images(text: str) -> str:
        used_labels: set[str] = set()
        result = text
        while True:
            for match in _IMG_REF.finditer(result):
                used_labels.add(match.group(2).lower())
            updated = _IMG_REF.sub(r"\1", _IMG_INLINE.sub(r"\1", result))
            if updated == result:
                break
            result = updated
        if used_labels:
            result = _REF_DEF.sub(
                lambda m: "" if m.group(1).lower() in used_labels else m.group(0),
                result,
            )
        return result

    def _sanitize_content(content: Any) -> tuple[Any, bool]:
        """Sanitize string or list-based message content. Returns (new_content, changed)."""
        if isinstance(content, str):
            sanitized = _strip_images(content)
            return sanitized, sanitized != content
        if isinstance(content, list):
            changed = False
            new_blocks: list[Any] = []
            for block in content:
                if isinstance(block, str):
                    sanitized = _strip_images(block)
                    if sanitized != block:
                        changed = True
                    new_blocks.append(sanitized)
                elif (
                    isinstance(block, dict)
                    and block.get("type") == "text"
                    and isinstance(block.get("text"), str)
                ):
                    sanitized = _strip_images(block["text"])
                    if sanitized != block["text"]:
                        changed = True
                        new_blocks.append({**block, "text": sanitized})
                    else:
                        new_blocks.append(block)
                else:
                    new_blocks.append(block)
            return new_blocks, changed
        return content, False

    class ImageSanitizeMiddleware(AgentMiddleware):
        """Strip markdown image tags from both user input and AI responses."""

        def before_model(self, state: Any, runtime: Any) -> Any:
            return self._sanitize_input(state)

        async def abefore_model(self, state: Any, runtime: Any) -> Any:
            return self._sanitize_input(state)

        def after_model(self, state: Any, runtime: Any) -> Any:
            return self._sanitize_output(state)

        async def aafter_model(self, state: Any, runtime: Any) -> Any:
            return self._sanitize_output(state)

        def _sanitize_input(self, state: Any) -> Any:
            from langchain_core.messages import HumanMessage, ToolMessage

            msgs = state.get("messages", []) if isinstance(state, dict) else []
            if not msgs:
                return None
            modified = False
            for i in range(len(msgs) - 1, -1, -1):
                msg = msgs[i]
                if isinstance(msg, (HumanMessage, ToolMessage)) and msg.content:
                    sanitized, changed = _sanitize_content(msg.content)
                    if changed:
                        label = (
                            "user input"
                            if isinstance(msg, HumanMessage)
                            else "tool result"
                        )
                        logger.warning("Stripped markdown image tag(s) from %s", label)
                        msgs[i] = msg.model_copy(update={"content": sanitized})
                        modified = True
            if not modified:
                return None
            return {"messages": msgs}

        def _sanitize_output(self, state: Any) -> Any:
            from langchain_core.messages import AIMessage

            msgs = state.get("messages", []) if isinstance(state, dict) else []
            if not msgs:
                return None
            last = msgs[-1]
            if not isinstance(last, AIMessage):
                return None
            if not last.content:
                return None
            sanitized, changed = _sanitize_content(last.content)
            if not changed:
                return None
            logger.warning("Stripped markdown image tag(s) from model response")
            msgs[-1] = last.model_copy(update={"content": sanitized})
            return {"messages": msgs}

    return ImageSanitizeMiddleware()


def _build_model_router_middleware() -> Any | None:
    """Per-request model tier selection, when router.yaml enables it."""
    try:
        from agent.src.routing import build_model_router_middleware

        return build_model_router_middleware()
    except Exception as exc:
        logger.error("Model router unavailable: %s", exc, exc_info=True)
        return None


def build_middleware_list(
    resolved: ResolvedMiddlewareConfig,
    *,
    model: Any | None = None,
    model_name: str = "",
    backend: Any | None = None,
    mcp_tool_names: frozenset[str] | None = None,
) -> list[Any]:
    """Build a list of middleware instances from resolved config."""
    middlewares: list[Any] = []

    audit_mw = build_audit_middleware(mcp_tool_names=mcp_tool_names)
    if audit_mw is not None:
        middlewares.append(audit_mw)

    opa_mw = build_opa_middleware()
    if opa_mw is not None:
        middlewares.append(opa_mw)

    router_mw = _build_model_router_middleware()
    if router_mw is not None:
        middlewares.append(router_mw)

    safety_mw = _build_gemini_safety_log_middleware()
    if safety_mw is not None:
        middlewares.append(safety_mw)

    identity_mw = build_user_identity_middleware()
    if identity_mw is not None:
        middlewares.append(identity_mw)

    agent_config_mw = build_agent_config_middleware()
    if agent_config_mw is not None:
        middlewares.append(agent_config_mw)

    datetime_mw = build_current_datetime_middleware()
    if datetime_mw is not None:
        middlewares.append(datetime_mw)

    prompt_size_mw = build_prompt_size_middleware()
    if prompt_size_mw is not None:
        middlewares.append(prompt_size_mw)

    from agent.aegra.mcp_tool_auth import build_mcp_auth_notice_middleware

    auth_notice_mw = build_mcp_auth_notice_middleware()
    if auth_notice_mw is not None:
        middlewares.append(auth_notice_mw)

    image_sanitize_mw = _build_image_sanitize_middleware()
    if image_sanitize_mw is not None:
        middlewares.append(image_sanitize_mw)

    nothing_to_send_mw = build_nothing_to_send_middleware()
    if nothing_to_send_mw is not None:
        middlewares.append(nothing_to_send_mw)

    fresh_run_mw = build_fresh_run_middleware()
    if fresh_run_mw is not None:
        middlewares.append(fresh_run_mw)

    if not settings.MIDDLEWARE_ENABLED:
        logger.info("Middleware disabled via MIDDLEWARE_ENABLED=false")
        return middlewares

    try:
        from agent.src.agent.reasoning_profiles import worth_offering
        from agent.src.routing.config import load_router_config

        offered = worth_offering(load_router_config().model_dump())
        effort_mw = build_reasoning_effort_middleware(
            [{"name": one.name, "effort": one.effort} for one in offered]
        )
        if effort_mw is not None:
            middlewares.append(effort_mw)
    except Exception:
        logger.debug("Could not build the reasoning-effort middleware", exc_info=True)

    from agent.src.agent.config import agent_config

    pii_cfg = agent_config.get_custom_pii_config()

    if pii_cfg.enabled:
        _append_if_built(middlewares, _build_custom_pii_middleware())

    if resolved.summarization_tool_enabled:
        _append_if_built(
            middlewares,
            _build_summarization_tool_middleware(model=model, backend=backend),
        )

    if model is not None and backend is not None:
        _append_if_built(
            middlewares,
            _build_configured_compaction(
                model=model, backend=backend, config=resolved.compaction
            ),
        )

    _append_if_built(middlewares, _build_block_budget(resolved))

    _append_if_built(middlewares, _build_tool_shortlist(resolved))

    _append_guardrails(middlewares, resolved, model_name)

    for entry in resolved.extra_middleware:
        if isinstance(entry, dict) and entry.get("url"):
            continue
        _append_if_built(middlewares, declared_extension(entry).load())

    from agent.src.infrastructure.remote_extension import (
        build_remote_extension_middleware,
        declared_remotes,
    )

    _append_if_built(
        middlewares,
        build_remote_extension_middleware(
            declared_remotes(list(resolved.extra_middleware or []))
        ),
    )

    if middlewares:
        logger.info("Built %d extra middleware instance(s)", len(middlewares))
    return middlewares


def _append_if_built(target: list[Any], mw: Any | None) -> None:
    """Append middleware to list if it was built successfully."""
    if mw is not None:
        target.append(mw)


def _append_guardrails(
    target: list[Any],
    resolved: ResolvedMiddlewareConfig,
    model_name: str = "",
) -> None:
    """Build and append all production guardrail middleware."""
    if resolved.model_call_limit.enabled:
        _append_if_built(
            target, _build_model_call_limit(resolved.model_call_limit.run_limit)
        )

    if resolved.tool_call_limit.enabled:
        _append_if_built(
            target, _build_tool_call_limit(resolved.tool_call_limit.run_limit)
        )
        for limiter in _build_per_tool_limits(resolved.tool_call_limit.per_tool):
            _append_if_built(target, limiter)

    for exclusion in _build_tool_exclusions(_profile_excluded_tools(model_name)):
        _append_if_built(target, exclusion)

    if resolved.spend_limit.enabled:
        _append_if_built(target, _build_spend_limit(resolved.spend_limit))

    if resolved.model_retry.enabled:
        _append_if_built(target, _build_model_retry(resolved.model_retry))

    if resolved.model_fallback.enabled and resolved.model_fallback.fallback_model:
        _append_if_built(
            target, _build_model_fallback(resolved.model_fallback.fallback_model)
        )

    if resolved.tool_retry.enabled and resolved.tool_retry.tools:
        _append_if_built(target, _build_tool_retry(resolved.tool_retry))

    from agent.src.agent.config import agent_config

    pii_cfg = agent_config.get_custom_pii_config()
    warn_if_unscrubbed(pii_cfg)
    if pii_cfg.enabled and pii_cfg.rules:
        target.extend(_build_pii_middleware(pii_cfg))


def build_excluded_middleware(
    resolved: ResolvedMiddlewareConfig,
) -> list[str]:
    """Build the list of middleware to exclude from deepagents defaults."""
    excluded: list[str] = list(resolved.excluded_middleware)

    if not resolved.patch_tool_calls_enabled:
        excluded.append("PatchToolCallsMiddleware")

    return excluded


def resolve_memory_param(
    resolved: ResolvedMiddlewareConfig,
) -> list[str] | None:
    """Resolve the memory= parameter for create_deep_agent()."""
    if not settings.MIDDLEWARE_ENABLED:
        return None
    if not resolved.memory_enabled:
        return None
    from agent.src.memory.instructions import resolve_memory_namespaces

    return resolve_memory_namespaces(resolved.memory_namespaces)


class SpendLimitUnusable(RuntimeError):
    """The configured spending ceiling cannot be read."""


def _per_caller_cap_is_set() -> bool:
    """Whether anything is reading a per-caller daily total."""
    from agent.src.agent.config import agent_config

    try:
        limits = agent_config.get_inbound_config().limits
        if limits is not None and limits.daily_spend is not None:
            return True
    except Exception:
        pass

    try:
        allowance = agent_config.get_limits_config()
    except Exception:
        return False
    return any(
        cap is not None
        for cap in (
            allowance.per_person,
            allowance.per_team,
            allowance.per_person_month,
            allowance.per_team_month,
        )
    )


async def _teams_with_a_budget(caller: str) -> tuple[str, ...]:
    """Which budgeted teams this person is in."""
    from agent.src.agent.config import agent_config
    from agent.src.ldap import resolve_user_groups

    allowance = agent_config.get_limits_config()
    if not allowance.teams:
        return ()
    return tuple(await resolve_user_groups(caller, allowance.teams))


async def _record_caller_spend(
    caller: str, amount: Any, *, context: dict[str, str] | None = None
) -> None:
    """Charge a run to the person, and to their team."""
    from agent.src.security.caller_spend import record

    await record(caller, amount)

    teams: tuple[str, ...] = ()
    try:
        teams = await _teams_with_a_budget(caller)
        for team in teams:
            await record(f"team:{team}", amount)
    except Exception as error:
        logger.warning("Could not charge %s to a team: %s", amount, error)

    await _bill_for(caller, amount, teams, context or {})


async def _bill_for(
    caller: str, amount: Any, teams: tuple[str, ...], context: dict[str, str]
) -> None:
    """Put the run on the month's bill, once, against one payer."""
    from agent.src.security import cost_attribution

    try:
        await cost_attribution.charge_for(
            cost_attribution.RunCost(
                run_id="",
                person=caller,
                team=teams[0] if teams else "",
                project=context.get("project", ""),
                amount=amount,
                started_by=context.get("started_by", "person"),
                space=context.get("space", ""),
            )
        )
    except Exception as error:
        logger.warning("Could not bill %s for %s: %s", caller, amount, error)


def _build_spend_limit(config: Any) -> Any | None:
    """Cap what one run may cost, in the rate card's currency."""
    counting = _per_caller_cap_is_set()

    if not getattr(config, "enabled", False):
        if not counting:
            return None
        from agent.src.security.spend_middleware import SpendLimitMiddleware

        return SpendLimitMiddleware(
            currency=settings.RATE_CARD_CURRENCY,
            on_spent=_record_caller_spend,
        )

    try:
        from agent.src.security.spend_middleware import SpendLimitMiddleware

        return SpendLimitMiddleware(
            warn_at=config.warning(),
            refuse_at=config.ceiling(),
            currency=settings.RATE_CARD_CURRENCY,
            on_spent=_record_caller_spend if counting else None,
        )
    except ValueError as error:
        raise SpendLimitUnusable(
            f"middleware.spend_limit is not usable: {error}. "
            "Fix the amounts, or remove the section to run without a ceiling."
        ) from error


def _build_model_call_limit(run_limit: int) -> Any | None:
    """Build ModelCallLimitMiddleware to cap LLM calls per run."""
    try:
        from langchain.agents.middleware import ModelCallLimitMiddleware

        return ModelCallLimitMiddleware(run_limit=run_limit)
    except ImportError:
        logger.debug("ModelCallLimitMiddleware not available")
        return None


def _build_tool_call_limit(run_limit: int) -> Any | None:
    """Build ToolCallLimitMiddleware to cap tool calls per run."""
    try:
        from langchain.agents.middleware import ToolCallLimitMiddleware

        return ToolCallLimitMiddleware(run_limit=run_limit)
    except ImportError:
        logger.debug("ToolCallLimitMiddleware not available")
        return None


def _build_per_tool_limits(per_tool: dict[str, int]) -> list[Any]:
    """Cap individual tools that loop."""
    built: list[Any] = []
    if not isinstance(per_tool, dict) or not per_tool:
        return built
    try:
        from langchain.agents.middleware import ToolCallLimitMiddleware
    except ImportError:
        logger.debug("ToolCallLimitMiddleware not available")
        return built

    for tool_name, limit in per_tool.items():
        if not isinstance(limit, int) or limit <= 0:
            continue
        built.append(
            ToolCallLimitMiddleware(
                tool_name=tool_name,
                run_limit=limit,
                exit_behavior="continue",
            )
        )
        logger.info("Tool call limit: %s capped at %d per run", tool_name, limit)
    return built


_policy_denied_tools: ContextVar[tuple[str, ...]] = ContextVar(
    "policy_denied_tools", default=()
)


def set_policy_denied_tools(names: Iterable[str]) -> None:
    """Record the tools the approval policy denies for this graph build."""
    _policy_denied_tools.set(tuple(sorted(set(names))))


def _profile_excluded_tools(model_name: str = "") -> list[str]:
    """Every tool to remove, whatever the reason."""
    names: set[str] = set()
    try:
        from agent.src.agent.config import agent_config

        profiles = agent_config.get_providers_config().harness_profiles or {}
        profile = profiles.get(model_name) if model_name else None
        if profile is not None:
            for tool in getattr(profile, "excluded_tools", None) or []:
                names.add(str(tool))
    except Exception:
        logger.debug("Could not read harness excluded tools", exc_info=True)

    try:
        from agent.src.agent.config import agent_config

        exclusion = agent_config.resolve_agent_middleware("", None).tool_exclusion
        if getattr(exclusion, "enabled", True):
            for tool in getattr(exclusion, "tools", None) or []:
                names.add(str(tool))
    except Exception:
        logger.debug("Could not read configured tool exclusions", exc_info=True)

    names.update(_policy_denied_tools.get())

    return sorted(names)


def _build_tool_exclusions(excluded: list[str]) -> list[Any]:
    """Remove named tools from an agent's reach."""
    if not excluded:
        return []
    try:
        from deepagents.middleware.tool_exclusion import ToolExclusionMiddleware
    except ImportError:
        try:
            from deepagents.graph import (
                _ToolExclusionMiddleware as ToolExclusionMiddleware,
            )
        except Exception:
            logger.warning("Tool exclusion middleware unavailable")
            return []
    logger.info("Excluding tools: %s", ", ".join(excluded))
    return [ToolExclusionMiddleware(excluded=excluded)]


def _build_block_budget(resolved: Any) -> Any | None:
    """Take a looping tool away for one call, when a ceiling is set."""
    config = getattr(resolved, "tool_call_limit", None)
    if config is None:
        return None

    per_block = int(getattr(config, "per_block", 0) or 0)
    per_thread = int(getattr(config, "per_thread", 0) or 0)
    if per_block <= 0 and per_thread <= 0:
        return None

    from agent.src.infrastructure.block_budget import BlockBudgetMiddleware

    for limit, scope in ((per_block, "block"), (per_thread, "conversation")):
        if limit > 0:
            logger.info("Tool budget: %d calls per %s", limit, scope)
    return BlockBudgetMiddleware(config=config)


def _build_tool_shortlist(resolved: Any) -> Any | None:
    """Narrow the advertised tool list, when a deployment asked for it."""
    config = getattr(resolved, "tool_shortlist", None)
    if config is None or getattr(config, "strategy", "none") == "none":
        return None

    from agent.src.agent.config import agent_config
    from agent.src.infrastructure.shortlist import (
        ToolShortlistMiddleware,
        tool_prefixes,
    )

    try:
        servers = agent_config.get_mcp_servers() or {}
        declared = tool_prefixes(
            list(agent_config.get_orchestrator_config().get("mcps") or []), servers
        )
        known = tool_prefixes(list(servers), servers)
    except Exception:
        logger.warning(
            "Tool shortlisting is configured but the servers "
            "could not be read; sending every tool"
        )
        return None

    logger.info(
        "Tool shortlisting '%s': %d declared of %d connected server(s)",
        config.strategy,
        len(declared),
        len(known),
    )
    return ToolShortlistMiddleware(
        config=config, declared_servers=declared, known_servers=known
    )


def _build_model_retry(config: Any) -> Any | None:
    """Build ModelRetryMiddleware for transient failure recovery."""
    try:
        from langchain.agents.middleware import ModelRetryMiddleware

        from agent.src.guardrails import (
            ContentSafetyError,
            InputContentSafetyError,
            ToolContentSafetyError,
        )

        def _on_failure(exc: Exception) -> str:
            if isinstance(exc, ToolContentSafetyError):
                return "I wasn't able to complete this task due to a content safety policy issue."
            if isinstance(exc, (InputContentSafetyError, ContentSafetyError)):
                return "I can't help with that request due to content safety policy."
            exc_type = type(exc).__name__
            logger.exception("Model call failed: %s: %s", exc_type, exc)
            return f"Model call failed with {exc_type}: {exc}"

        return ModelRetryMiddleware(
            max_retries=config.max_retries,
            backoff_factor=config.backoff_factor,
            initial_delay=config.initial_delay,
            retry_on=lambda exc: not isinstance(exc, ContentSafetyError),
            on_failure=_on_failure,
        )
    except ImportError:
        logger.debug("ModelRetryMiddleware not available")
        return None


def _build_model_fallback(fallback_model: str) -> Any | None:
    """Build ModelFallbackMiddleware to switch models on primary failure."""
    try:
        from langchain.agents.middleware import ModelFallbackMiddleware

        return ModelFallbackMiddleware(fallback_model)
    except ImportError:
        logger.debug("ModelFallbackMiddleware not available")
        return None
    except Exception as e:
        logger.warning("ModelFallbackMiddleware init failed (check model auth): %s", e)
        return None


def _build_tool_retry(config: Any) -> Any | None:
    """Build ToolRetryMiddleware for specific tools."""
    try:
        from langchain.agents.middleware import ToolRetryMiddleware

        return ToolRetryMiddleware(
            max_retries=config.max_retries,
            tools=config.tools,
        )
    except ImportError:
        logger.debug("ToolRetryMiddleware not available")
        return None


class PIIProtectionUnavailable(RuntimeError):
    """PII scrubbing was asked for and could not be built."""


def _build_custom_pii_middleware() -> Any:
    """Build the custom token-map PIIMiddleware from the global scrubber."""
    try:
        from agent.src.pii.middleware import build_pii_middleware

        return build_pii_middleware()
    except ImportError as error:
        raise PIIProtectionUnavailable(
            f"PII scrubbing is enabled but could not be built: {error}. "
            "Install what it needs, or set pii.enabled to false to run "
            "without it deliberately."
        ) from error


def warn_if_unscrubbed(config: Any) -> None:
    """Say so when nothing will mask personal data."""
    try:
        if getattr(config, "enabled", False):
            if getattr(config, "rules", None):
                return
            logger.warning(
                "Personal data is not being masked: scrubbing is switched on but "
                "no rules are configured, so text reaches the model and the trace "
                "unchanged."
            )
            return

        logger.warning(
            "Personal data is not being masked: scrubbing is switched off, so "
            "text reaches the model and the trace unchanged."
        )
    except Exception:
        logger.debug("Could not check whether scrubbing is configured", exc_info=True)


def _build_pii_middleware(config: Any) -> list[Any]:
    """Route rules by provider."""
    try:
        from langchain.agents.middleware import AgentMiddleware, PIIMiddleware

        instances = []
        for rule in config.rules:
            if getattr(rule, "provider", "default") != "default":
                continue
            try:
                instances.append(
                    PIIMiddleware(
                        rule.name, strategy=rule.strategy, apply_to_input=True
                    )
                )
            except (ValueError, TypeError) as e:
                logger.warning("Skipping PII rule '%s': %s", rule.name, e)

        if not instances:
            return []

        class ParallelPIIMiddleware(AgentMiddleware):
            """Runs all stock PII type checks concurrently instead of as a sequential chain."""

            async def abefore_model(self, state: Any, runtime: Any) -> Any:
                import asyncio

                results = await asyncio.gather(
                    *(inst.abefore_model(state, runtime) for inst in instances),
                    return_exceptions=True,
                )
                for r in results:
                    if isinstance(r, BaseException):
                        raise r
                merged: dict = {}
                for r in results:
                    if isinstance(r, dict):
                        merged.update(r)
                return merged or None

            def before_model(self, state: Any, runtime: Any) -> Any:
                from concurrent.futures import ThreadPoolExecutor

                with ThreadPoolExecutor() as pool:
                    futures = [
                        pool.submit(inst.before_model, state, runtime)
                        for inst in instances
                    ]
                    results = [f.result() for f in futures]
                for r in results:
                    if isinstance(r, BaseException):
                        raise r
                merged: dict = {}
                for r in results:
                    if isinstance(r, dict):
                        merged.update(r)
                return merged or None

        return [ParallelPIIMiddleware()]

    except ImportError:
        logger.debug("PIIMiddleware not available")
        return []


class CompactionUnavailable(RuntimeError):
    """Compaction was asked for and could not be built."""


def _build_configured_compaction(
    *,
    model: Any,
    backend: Any,
    config: Any,
) -> Any | None:
    """Compaction on this deployment's thresholds, or None for the defaults."""
    if not getattr(config, "configured", False):
        return None

    settings_given: dict[str, Any] = {}
    trigger = config.trigger()
    if trigger is not None:
        settings_given["trigger"] = trigger
    keep = config.keep()
    if keep is not None:
        settings_given["keep"] = keep

    try:
        from langchain.agents.middleware.summarization import SummarizationMiddleware

        return SummarizationMiddleware(model=model, backend=backend, **settings_given)
    except ImportError as error:
        raise CompactionUnavailable(
            "Compaction thresholds are configured but this runtime "
            "does not provide compaction"
        ) from error
    except Exception as error:
        raise CompactionUnavailable(
            f"Compaction thresholds are configured but could not be applied: {error}"
        ) from error


def _build_summarization_tool_middleware(
    *,
    model: Any | None = None,
    backend: Any | None = None,
) -> Any:
    """Build SummarizationToolMiddleware instance."""
    if model is None or backend is None:
        missing = "model" if model is None else "backend"
        raise CompactionUnavailable(
            f"Compaction is enabled but has no {missing} to work with"
        )
    try:
        from deepagents.middleware.summarization import (
            create_summarization_tool_middleware,
        )

        return create_summarization_tool_middleware(model, backend)
    except ImportError as error:
        raise CompactionUnavailable(
            "Compaction is enabled but this runtime does not provide it"
        ) from error
    except Exception as error:
        raise CompactionUnavailable(
            f"Compaction is enabled but could not be built: {error}"
        ) from error


def _import_middleware(dotted_path: str) -> Any | None:
    """Import and instantiate a middleware from a dotted path."""
    try:
        if ":" not in dotted_path:
            logger.warning(
                "Invalid middleware path '%s' — expected 'module:Class'", dotted_path
            )
            return None

        module_path, attr_name = dotted_path.rsplit(":", 1)
        module = importlib.import_module(module_path)
        factory_or_class = getattr(module, attr_name)

        if callable(factory_or_class):
            return factory_or_class()
        return factory_or_class
    except Exception as e:
        logger.warning("Failed to import middleware '%s': %s", dotted_path, e)
        return None


def build_reasoning_effort_middleware(profiles: list[dict[str, Any]]) -> Any | None:
    """Apply the way of answering a conversation chose."""
    if not profiles:
        return None

    try:
        from langchain.agents.middleware.types import (
            AgentMiddleware,
            ModelRequest,
            ModelResponse,
        )
    except ImportError:
        return None

    from agent.src.agent.reasoning_profiles import budget_for_effort

    efforts = {
        str(one.get("name", "")): str(one.get("effort", ""))
        for one in profiles
        if isinstance(one, dict) and one.get("name")
    }

    def _budget(runtime: Any) -> int | None:
        """The budget this run asked for, or nothing to leave it alone."""
        try:
            chosen = (
                (runtime.config or {}).get("configurable", {}).get("reasoning_profile")
            )
        except Exception:
            return None
        if not chosen or chosen not in efforts:
            return None
        return budget_for_effort(efforts[chosen])

    class ReasoningEffortMiddleware(AgentMiddleware):
        def _applied(
            self, request: ModelRequest[Any], runtime: Any
        ) -> ModelRequest[Any]:
            """Swap in a model built with this run's budget."""
            budget = _budget(runtime)
            if budget is None:
                return request

            current = getattr(request, "model", None)
            name = getattr(current, "model", None) or getattr(
                current, "model_name", None
            )
            if not name:
                return request

            try:
                from agent.src.agent.llm import create_model

                return request.override(
                    model=create_model(
                        model_name=str(name),
                        temperature=float(getattr(current, "temperature", 0.0) or 0.0),
                        thinking_budget=budget,
                    )
                )
            except Exception:
                logger.debug(
                    "Could not build a model for the chosen profile", exc_info=True
                )
                return request

        def wrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
            runtime: Any = None,
        ) -> ModelResponse[Any]:
            return handler(self._applied(request, runtime))

        async def awrap_model_call(
            self,
            request: ModelRequest[Any],
            handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
            runtime: Any = None,
        ) -> ModelResponse[Any]:
            return await handler(self._applied(request, runtime))

    return ReasoningEffortMiddleware()
