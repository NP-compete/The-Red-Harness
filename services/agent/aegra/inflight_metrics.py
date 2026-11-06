"""Expose how much work is in flight, so autoscaling can measure it."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

REFRESH_INTERVAL_SECONDS = settings.INFLIGHT_METRIC_INTERVAL_SECONDS
_ACTIVE_STATUSES = ("pending", "running")

_gauge: Any = None
_pod_gauge: Any = None
_task: asyncio.Task[None] | None = None


def _get_gauge() -> Any:
    """Lazily create the gauge so importing this module is side-effect free."""
    global _gauge  # noqa: PLW0603
    if _gauge is None:
        import prometheus_client

        _gauge = prometheus_client.Gauge(
            "aegra_runs_in_flight",
            "Runs currently pending or running, across all instances",
        )
    return _gauge


def _get_pod_gauge() -> Any:
    """This pod's own share, for the HPA."""
    global _pod_gauge  # noqa: PLW0603
    if _pod_gauge is None:
        import prometheus_client

        _pod_gauge = prometheus_client.Gauge(
            "aegra_runs_in_flight_pod",
            "Runs this instance is executing right now",
        )
    return _pod_gauge


def count_pod_active_runs() -> int:
    """Runs this process is executing, from Aegra's in-memory registry."""
    try:
        from agent.aegra.lifecycle import _get_active_runs

        return len(_get_active_runs() or {})
    except Exception:
        logger.debug("Could not read this pod's active runs", exc_info=True)
        return 0


async def count_active_runs() -> int:
    """Runs pending or running right now."""
    from aegra_api.core.orm import Run as RunORM
    from aegra_api.core.orm import _get_session_maker
    from sqlalchemy import func, select

    maker = _get_session_maker()
    async with maker() as session:
        result = await session.execute(
            select(func.count())
            .select_from(RunORM)
            .where(RunORM.status.in_(_ACTIVE_STATUSES))
        )
        return int(result.scalar() or 0)


async def _refresh_loop() -> None:
    """Keep the gauge current until cancelled."""
    gauge = _get_gauge()
    pod_gauge = _get_pod_gauge()
    while True:
        try:
            gauge.set(await count_active_runs())
            pod_gauge.set(count_pod_active_runs())
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Could not refresh in-flight gauge: %s", exc)
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


def start_inflight_metrics() -> None:
    """Begin publishing the gauge. Safe to call more than once."""
    global _task  # noqa: PLW0603
    if _task is not None and not _task.done():
        return

    _get_gauge()
    _task = asyncio.create_task(_refresh_loop())
    logger.info("Publishing aegra_runs_in_flight every %ds", REFRESH_INTERVAL_SECONDS)


async def stop_inflight_metrics() -> None:
    """Stop publishing, for a clean shutdown."""
    global _task  # noqa: PLW0603
    if _task is None:
        return
    _task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _task
    _task = None
