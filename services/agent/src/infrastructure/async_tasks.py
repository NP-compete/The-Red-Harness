"""Async subagent middleware builder."""

from __future__ import annotations

from typing import Any

from agent.src.agent.config.providers import AsyncTaskConfig
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()


def build_async_middleware(
    subagents: list[Any] | None,
    async_config: AsyncTaskConfig,
) -> Any | None:
    """Build AsyncSubAgentMiddleware if async subagents exist."""
    if not async_config.enabled:
        logger.debug("Async tasks disabled via config")
        return None

    if not subagents:
        return None

    async_subagents = _extract_async_subagents(subagents)
    if not async_subagents:
        return None

    try:
        from deepagents.middleware.async_subagents import AsyncSubAgentMiddleware

        kwargs: dict[str, Any] = {"async_subagents": async_subagents}
        if async_config.system_prompt is not None:
            kwargs["system_prompt"] = async_config.system_prompt

        middleware = AsyncSubAgentMiddleware(**kwargs)
        logger.info(
            "Built AsyncSubAgentMiddleware with %d async subagent(s)",
            len(async_subagents),
        )
        return middleware
    except ImportError:
        logger.warning("AsyncSubAgentMiddleware not available — async tasks disabled")
        return None
    except Exception as e:
        logger.warning("Failed to build AsyncSubAgentMiddleware: %s", e)
        return None


def _extract_async_subagents(subagents: list[Any]) -> list[Any]:
    """Filter the subagent list for AsyncSubAgent dicts."""
    return [s for s in subagents if isinstance(s, dict) and "graph_id" in s]
