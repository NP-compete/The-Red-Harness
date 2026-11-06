"""Make `/runs/wait` notice a finished run promptly."""

from __future__ import annotations

import asyncio
from typing import Any

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_patched = False


def _backoff_schedule() -> list[float]:
    """Sleep intervals, doubling from the floor up to the ceiling."""
    delays: list[float] = []
    delay = settings.RUN_WAIT_MIN_POLL_SECONDS
    while delay < settings.RUN_WAIT_MAX_POLL_SECONDS:
        delays.append(delay)
        delay *= 2
    delays.append(settings.RUN_WAIT_MAX_POLL_SECONDS)
    return delays


def install_fast_run_wait() -> str:
    """Replace the flat 2s poll with an adaptive one. Idempotent."""
    global _patched  # noqa: PLW0603
    if _patched:
        return "ok: already patched"
    if not settings.RUN_WAIT_FAST_POLL:
        return "skipped: disabled"

    try:
        from aegra_api.core.redis_manager import (
            redis_manager,
        )
        from aegra_api.services.worker_executor import (
            WorkerExecutor,
            _is_run_terminal,
        )
        from aegra_api.settings import (
            settings as aegra_settings,
        )
        from redis.exceptions import RedisError
    except Exception as exc:
        logger.warning("Fast run-wait not installed: %s", exc)
        return f"skipped: {exc}"

    async def wait_for_completion(
        self: Any, run_id: str, *, timeout: float = 300.0
    ) -> None:
        """Wait for a run to finish, checking often at first."""
        done_key = f"{aegra_settings.redis.REDIS_CHANNEL_PREFIX}done:{run_id}"
        client = redis_manager.get_client()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout

        delays = _backoff_schedule()
        index = 0
        next_db_check = loop.time() + settings.RUN_WAIT_DB_CHECK_SECONDS

        while loop.time() < deadline:
            try:
                if await client.exists(done_key):
                    return
            except RedisError:
                pass

            now = loop.time()
            if now >= next_db_check:
                next_db_check = now + settings.RUN_WAIT_DB_CHECK_SECONDS
                if await _is_run_terminal(run_id):
                    return

            await asyncio.sleep(delays[index])
            if index < len(delays) - 1:
                index += 1

        raise TimeoutError(f"Run {run_id} did not complete within {timeout}s")

    WorkerExecutor.wait_for_completion = wait_for_completion
    _patched = True
    logger.info(
        "Fast run-wait installed: first poll after %.0fms, backing off to %.1fs",
        settings.RUN_WAIT_MIN_POLL_SECONDS * 1000,
        settings.RUN_WAIT_MAX_POLL_SECONDS,
    )
    return "ok"
