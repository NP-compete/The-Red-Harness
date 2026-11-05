"""Per-run token and model usage, recorded where the tokens are spent."""

from __future__ import annotations

import asyncio
from typing import Any

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_RECORD_SQL = """
UPDATE runs
SET execution_params =
    COALESCE(execution_params, '{}'::jsonb)
    || jsonb_build_object('usage',
        COALESCE(execution_params -> 'usage', '{}'::jsonb)
        || jsonb_build_object(
            'input_tokens',
                COALESCE((execution_params #>> '{usage,input_tokens}')::bigint, 0)
                + %(input_tokens)s::bigint,
            'output_tokens',
                COALESCE((execution_params #>> '{usage,output_tokens}')::bigint, 0)
                + %(output_tokens)s::bigint,
            'cached_tokens',
                COALESCE((execution_params #>> '{usage,cached_tokens}')::bigint, 0)
                + %(cached_tokens)s::bigint,
            'calls',
                COALESCE((execution_params #>> '{usage,calls}')::bigint, 0) + 1,
            'models',
                COALESCE(execution_params #> '{usage,models}', '{}'::jsonb)
                || jsonb_build_object(%(model)s::text, jsonb_build_object(
                    'input_tokens',
                        COALESCE((execution_params #> '{usage,models}'
                                  -> %(model)s::text ->> 'input_tokens')::bigint, 0)
                        + %(input_tokens)s::bigint,
                    'output_tokens',
                        COALESCE((execution_params #> '{usage,models}'
                                  -> %(model)s::text ->> 'output_tokens')::bigint, 0)
                        + %(output_tokens)s::bigint,
                    'cached_tokens',
                        COALESCE((execution_params #> '{usage,models}'
                                  -> %(model)s::text ->> 'cached_tokens')::bigint, 0)
                        + %(cached_tokens)s::bigint,
                    'calls',
                        COALESCE((execution_params #> '{usage,models}'
                                  -> %(model)s::text ->> 'calls')::bigint, 0) + 1
                ))
        ))
WHERE run_id = %(run_id)s::text
"""

_failures = 0
_FAILURE_ALERT_THRESHOLD = settings.USAGE_FAILURE_ALERT_THRESHOLD
_ACQUIRE_TIMEOUT_SECONDS = 2.0
_WRITE_TIMEOUT_SECONDS = 5.0


async def _get_pool() -> Any:
    """The process-wide pool."""
    from agent.src.db.pool import get_pool as get_shared_pool

    return await get_shared_pool()


async def close_pool() -> None:
    """Retained for callers that close analytics explicitly."""
    return None


async def record_llm_usage(
    run_id: str,
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> None:
    """Add one model call's tokens to its run."""
    global _failures  # noqa: PLW0603
    if not run_id:
        return
    params = {
        "run_id": run_id,
        "model": model or "unknown",
        "input_tokens": max(0, int(input_tokens or 0)),
        "output_tokens": max(0, int(output_tokens or 0)),
        "cached_tokens": max(0, int(cached_tokens or 0)),
    }
    try:
        pool = await _get_pool()
        async with asyncio.timeout(_WRITE_TIMEOUT_SECONDS):
            async with pool.connection(timeout=_ACQUIRE_TIMEOUT_SECONDS) as conn:
                await conn.execute(_RECORD_SQL, params)
        _failures = 0
    except Exception as exc:
        _failures += 1
        if _failures >= _FAILURE_ALERT_THRESHOLD:
            logger.error("usage_recording_degraded", consecutive_failures=_failures)
        else:
            logger.warning(
                "Failed to record usage for run %s: %s", run_id, exc, exc_info=True
            )
