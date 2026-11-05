"""One Postgres pool for everything in agent that is not LangGraph."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import psycopg
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from agent.src.settings import settings
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

DictPool = AsyncConnectionPool[psycopg.AsyncConnection[DictRow]]

_pool: DictPool | None = None
_lock = asyncio.Lock()


async def _configure(conn: Any) -> None:
    """Run once per new connection, not per checkout."""
    if settings.DB_STATEMENT_TIMEOUT_MS > 0:
        await conn.execute(
            f"SET statement_timeout = {int(settings.DB_STATEMENT_TIMEOUT_MS)}"
        )


async def get_pool() -> DictPool:
    """Return the shared pool, opening it on first use."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        return _pool
    async with _lock:
        if _pool is None:
            pool: DictPool = AsyncConnectionPool(
                settings.database_uri,
                min_size=settings.DB_POOL_MIN_SIZE,
                max_size=settings.DB_POOL_MAX_SIZE,
                timeout=settings.DB_POOL_TIMEOUT,
                max_idle=settings.DB_POOL_MAX_IDLE,
                max_lifetime=settings.DB_POOL_MAX_LIFETIME,
                check=AsyncConnectionPool.check_connection,
                configure=_configure,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": None,
                    "row_factory": dict_row,
                    "keepalives": 1,
                    "keepalives_idle": 300,
                    "keepalives_interval": 30,
                    "keepalives_count": 3,
                },
                open=False,
            )
            await pool.open()
            _pool = pool
            logger.info(
                "Postgres pool open: min=%d max=%d timeout=%.1fs "
                "statement_timeout=%dms",
                settings.DB_POOL_MIN_SIZE,
                settings.DB_POOL_MAX_SIZE,
                settings.DB_POOL_TIMEOUT,
                settings.DB_STATEMENT_TIMEOUT_MS,
            )
    return _pool


@asynccontextmanager
async def connection(row_factory: Any = None) -> AsyncIterator[Any]:
    """Borrow a connection, returning it on success or on exception."""
    pool = await get_pool()
    async with pool.connection() as conn:
        if row_factory is None:
            yield conn
            return
        previous = conn.row_factory
        conn.row_factory = row_factory
        try:
            yield conn
        finally:
            conn.row_factory = previous


async def close_pool() -> None:
    """Release the pool on shutdown."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool_stats() -> dict[str, Any]:
    """Pool counters for health and metrics, or empty if never opened."""
    if _pool is None:
        return {}
    stats = _pool.get_stats()
    return {
        "size": stats.get("pool_size", 0),
        "available": stats.get("pool_available", 0),
        "waiting": stats.get("requests_waiting", 0),
        "max_size": settings.DB_POOL_MAX_SIZE,
    }
