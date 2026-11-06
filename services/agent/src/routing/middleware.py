"""Model routing middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain.agents.middleware.types import (
        ModelCallResult,
        ModelRequest,
        ModelResponse,
    )

from agent.src.routing.classifier import choose_tier
from agent.src.routing.config import RouterConfig, load_router_config
from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

STATE_KEY = settings.ROUTING_STATE_KEY

_ROUTED_TIERS: dict[str, str] = {}
_ROUTED_TIERS_LIMIT = 2048


def _thread_id() -> str:
    """The current thread, or "" when there is no graph context."""
    try:
        from langgraph.config import get_config

        config = get_config() or {}
        return str((config.get("configurable") or {}).get("thread_id") or "")
    except Exception:
        return ""


def _first_human_text(messages: list[Any]) -> str:
    """The text that routing is decided on."""
    for message in messages:
        mtype = getattr(message, "type", None) or (
            message.get("type") if isinstance(message, dict) else None
        )
        role = getattr(message, "role", None) or (
            message.get("role") if isinstance(message, dict) else None
        )
        if mtype in ("human", "user") or role in ("human", "user"):
            content = getattr(message, "content", None)
            if content is None and isinstance(message, dict):
                content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return " ".join(
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict)
                )
    return ""


def _latest_human_text(messages: list[Any]) -> str:
    """The most recent user turn, for per-turn routing."""
    return _first_human_text(list(reversed(messages)))


def build_model_router_middleware(
    config: RouterConfig | None = None,
) -> Any | None:
    """Build the routing middleware, or ``None`` when routing is off."""
    cfg = config or load_router_config()

    if not cfg.enabled or len(cfg.tiers) < 2:
        return None

    try:
        from langchain.agents.middleware import wrap_model_call
    except ImportError:
        logger.warning("wrap_model_call unavailable — model routing disabled")
        return None

    from agent.src.agent.llm import create_model

    clients: dict[str, Any] = {}

    def _client_for(tier_name: str) -> Any | None:
        if tier_name in clients:
            return clients[tier_name]
        tier = cfg.tier_by_name(tier_name)
        if tier is None:
            return None
        try:
            kwargs: dict[str, Any] = {"model_name": tier.model}
            if tier.max_output_tokens:
                kwargs["max_output_tokens"] = tier.max_output_tokens
            clients[tier_name] = create_model(**kwargs)
        except Exception as exc:
            logger.error("Could not build model for tier '%s': %s", tier_name, exc)
            clients[tier_name] = None
        return clients[tier_name]

    def _annotate(response: Any, fields: dict[str, Any]) -> None:
        """Attach fields to the returned message, best effort."""
        message = getattr(response, "result", None) or response
        if isinstance(message, list) and message:
            message = message[0]
        existing = getattr(message, "additional_kwargs", None)
        if isinstance(existing, dict):
            existing.update(fields)

    async def route(
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
    ) -> ModelCallResult:
        state = getattr(request, "state", None) or {}
        messages = list(getattr(request, "messages", []) or [])

        thread = _thread_id()
        remembered = state.get(STATE_KEY) if isinstance(state, dict) else None
        if not remembered and thread:
            remembered = _ROUTED_TIERS.get(thread)

        if cfg.strategy == "first_message" and remembered:
            chosen_name, reason, method = remembered, "already routed", "sticky"
        else:
            text = (
                _latest_human_text(messages)
                if cfg.strategy == "every_turn"
                else _first_human_text(messages)
            )
            decision = await choose_tier(text, cfg)
            chosen_name = decision.tier.name
            reason, method = decision.reason, decision.method

            logger.info("Routed to tier '%s' (%s: %s)", chosen_name, method, reason)

            if thread and cfg.strategy == "first_message":
                if len(_ROUTED_TIERS) >= _ROUTED_TIERS_LIMIT:
                    for stale in list(_ROUTED_TIERS)[: _ROUTED_TIERS_LIMIT // 2]:
                        _ROUTED_TIERS.pop(stale, None)
                _ROUTED_TIERS[thread] = chosen_name

        client = _client_for(chosen_name)
        if client is None:
            logger.warning(
                "Tier '%s' has no usable model — using the agent's default",
                chosen_name,
            )
            return await handler(request)

        routed = request.override(model=client)
        response = await handler(routed)

        _annotate(response, {"routed_tier": chosen_name, "routed_by": method})
        return response

    # `route` matches `_AsyncCallableReturningModelResponse`, but with no
    # `state_schema` the decorator's `StateT` is unsolvable and no overload
    # can be selected.
    middleware = wrap_model_call(  # type: ignore[call-overload]
        route, name="ModelRouterMiddleware"
    )
    logger.info(
        "Model router active: %s",
        ", ".join(f"{t.name}={t.model}" for t in cfg.tiers),
    )
    return middleware
