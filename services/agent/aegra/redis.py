"""Redis connection configuration for aegra deployment (MR-20)."""

import asyncio
import functools
import os
import secrets
import threading
import time
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, Literal, TypeVar

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_T = TypeVar("_T")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REDIS_MAX_CONNECTIONS = int(os.environ.get("REDIS_MAX_CONNECTIONS", "10"))
REDIS_SOCKET_TIMEOUT = int(os.environ.get("REDIS_SOCKET_TIMEOUT", "5"))
REDIS_RETRY_ON_TIMEOUT = (
    os.environ.get("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
)
REDIS_KEY_PREFIX = os.environ.get("REDIS_KEY_PREFIX", "aegra:")

_executor: Any = None
_executor_lock = threading.Lock()

_client: Any = None
_async_client: Any = None
_async_client_loop: Any = None
_async_lock = asyncio.Lock()


def _get_executor() -> Any:
    """The dedicated Redis thread pool, created on first use."""
    global _executor  # noqa: PLW0603
    if _executor is not None:
        return _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=max(2, REDIS_MAX_CONNECTIONS),
                thread_name_prefix="redis",
            )
    return _executor


async def run_redis(fn: Callable[..., _T], /, *args: Any, **kwargs: Any) -> _T:
    """Await a blocking Redis helper on the dedicated executor."""
    loop = asyncio.get_running_loop()
    call = functools.partial(fn, *args, **kwargs)
    return await loop.run_in_executor(_get_executor(), call)


async def get_async_redis_client() -> Any:
    """Get or create the asyncio Redis client, or None if unavailable."""
    global _async_client, _async_client_loop  # noqa: PLW0603

    loop = asyncio.get_running_loop()
    if _async_client is not None and _async_client_loop is loop:
        return _async_client

    async with _async_lock:
        if _async_client is not None and _async_client_loop is not loop:
            _async_client = None
        if _async_client is None:
            try:
                import redis.asyncio as aioredis

                client = aioredis.from_url(
                    REDIS_URL,
                    max_connections=REDIS_MAX_CONNECTIONS,
                    socket_timeout=REDIS_SOCKET_TIMEOUT,
                    retry_on_timeout=REDIS_RETRY_ON_TIMEOUT,
                    decode_responses=True,
                )
                await client.ping()
                _async_client = client
                _async_client_loop = loop
                logger.info("Redis (async) connected: %s", REDIS_URL)
            except Exception:
                logger.warning(
                    "Async Redis unavailable at %s", REDIS_URL, exc_info=True
                )
                return None
    return _async_client


async def close_async_redis_client() -> None:
    """Close the asyncio Redis client. Idempotent."""
    global _async_client, _async_client_loop  # noqa: PLW0603
    if _async_client is None:
        return
    try:
        await _async_client.aclose()
        logger.info("Async Redis client closed")
    except Exception:
        logger.debug("Async Redis close error", exc_info=True)
    finally:
        _async_client = None
        _async_client_loop = None


def get_redis_config() -> dict[str, Any]:
    """Return the Redis configuration dict for documentation/debugging."""
    return {
        "url": REDIS_URL,
        "max_connections": REDIS_MAX_CONNECTIONS,
        "socket_timeout": REDIS_SOCKET_TIMEOUT,
        "retry_on_timeout": REDIS_RETRY_ON_TIMEOUT,
        "key_prefix": REDIS_KEY_PREFIX,
    }


_UNAVAILABLE_FOR_SECONDS = 5.0
_unavailable_until: float = 0.0


def get_redis_client() -> Any:
    """Get or create a Redis client with connection pooling."""
    global _client, _unavailable_until  # noqa: PLW0603
    if _client is not None:
        return _client
    if time.monotonic() < _unavailable_until:
        return None

    try:
        import redis

        _client = redis.from_url(
            REDIS_URL,
            max_connections=REDIS_MAX_CONNECTIONS,
            socket_timeout=REDIS_SOCKET_TIMEOUT,
            retry_on_timeout=REDIS_RETRY_ON_TIMEOUT,
            decode_responses=True,
        )
        _client.ping()
        logger.info("Redis connected: %s", REDIS_URL)
        return _client
    except ImportError:
        logger.warning("redis package not installed — caching disabled")
        return None
    except Exception:
        logger.warning(
            "Redis unavailable at %s — caching disabled for %.0fs",
            REDIS_URL,
            _UNAVAILABLE_FOR_SECONDS,
            exc_info=True,
        )
        _client = None
        _unavailable_until = time.monotonic() + _UNAVAILABLE_FOR_SECONDS
        return None


def close_redis_client() -> None:
    """Close the Redis client connection if open. Idempotent."""
    global _client  # noqa: PLW0603
    if _client is None:
        return
    try:
        _client.close()
        logger.info("Redis client closed")
    except Exception:
        logger.debug("Redis close error", exc_info=True)
    finally:
        _client = None


def cache_get(key: str) -> str | None:
    """Read a value from Redis cache. Returns None on miss or error."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        val = client.get(f"{REDIS_KEY_PREFIX}{key}")
        return str(val) if val is not None else None
    except Exception:
        logger.debug("Cache read failed for key '%s'", key, exc_info=True)
        return None


def cache_set(key: str, value: str, ttl_seconds: int = 300) -> bool:
    """Write a value to Redis cache with TTL. Returns False on error."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.setex(f"{REDIS_KEY_PREFIX}{key}", ttl_seconds, value)
        return True
    except Exception:
        logger.debug("Cache write failed for key '%s'", key, exc_info=True)
        return False


def cache_set_persistent(key: str, value: str) -> bool:
    """Write a value to Redis without expiry. Returns False on error."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.set(f"{REDIS_KEY_PREFIX}{key}", value)
        return True
    except Exception:
        logger.debug("Persistent cache write failed for key '%s'", key, exc_info=True)
        return False


def cache_delete(key: str) -> bool:
    """Delete a key from Redis cache. Returns False on error."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.delete(f"{REDIS_KEY_PREFIX}{key}")
        return True
    except Exception:
        return False


def cache_sadd(key: str, value: str, ttl_seconds: int | None = None) -> bool:
    """Add a value to a Redis set. Optionally set/refresh key TTL."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.sadd(f"{REDIS_KEY_PREFIX}{key}", value)
        if ttl_seconds is not None:
            client.expire(f"{REDIS_KEY_PREFIX}{key}", ttl_seconds)
        return True
    except Exception:
        logger.debug("SADD failed for key '%s'", key, exc_info=True)
        return False


def cache_srem(key: str, value: str) -> bool:
    """Remove a value from a Redis set. Returns False on error."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.srem(f"{REDIS_KEY_PREFIX}{key}", value)
        return True
    except Exception:
        logger.debug("SREM failed for key '%s'", key, exc_info=True)
        return False


def cache_smembers(key: str) -> set[str] | None:
    """Return all members of a Redis set, or None on error."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        return client.smembers(f"{REDIS_KEY_PREFIX}{key}") or set()
    except Exception:
        logger.debug("SMEMBERS failed for key '%s'", key, exc_info=True)
        return None


def cache_expire(key: str, ttl_seconds: int) -> bool:
    """Set or refresh the TTL on an existing key. Returns False on error."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.expire(f"{REDIS_KEY_PREFIX}{key}", ttl_seconds)
        return True
    except Exception:
        logger.debug("EXPIRE failed for key '%s'", key, exc_info=True)
        return False


_RELEASE_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


def _lock_key(name: str) -> str:
    return f"{REDIS_KEY_PREFIX}lock:{name}"


def claim_once(key: str, *, ttl_seconds: int) -> bool | None:
    """Claim a key exactly once across every pod (SCALE-1)."""
    client = get_redis_client()
    if client is None:
        return None
    try:
        return bool(
            client.set(f"{REDIS_KEY_PREFIX}{key}", "1", nx=True, ex=ttl_seconds)
        )
    except Exception:
        logger.debug("Could not claim '%s'", key, exc_info=True)
        return None


def acquire_distributed_lock(
    name: str,
    *,
    ttl_seconds: int = 30,
    wait_seconds: float = 10.0,
    poll_interval: float = 0.05,
) -> str | None:
    """Acquire a Redis lock. Returns a token, or None if unavailable or timed out."""
    client = get_redis_client()
    if client is None:
        return None

    token = secrets.token_urlsafe(16)
    key = _lock_key(name)
    deadline = time.monotonic() + wait_seconds

    while True:
        try:
            if client.set(key, token, nx=True, ex=ttl_seconds):
                return token
        except Exception:
            logger.debug("Lock acquire failed for '%s'", name, exc_info=True)
            return None

        if time.monotonic() >= deadline:
            return None
        time.sleep(poll_interval)


def release_distributed_lock(name: str, token: str) -> bool:
    """Release a Redis lock when the token still matches."""
    client = get_redis_client()
    if client is None:
        return False
    try:
        return bool(client.eval(_RELEASE_LOCK_LUA, 1, _lock_key(name), token))
    except Exception:
        logger.debug("Lock release failed for '%s'", name, exc_info=True)
        return False


LockState = Literal["held", "no_redis", "timeout"]


async def _acquire_lock_async(
    client: Any,
    name: str,
    *,
    ttl_seconds: int,
    wait_seconds: float,
    poll_interval: float = 0.05,
) -> str | None:
    """Poll for the lock without occupying a thread."""
    token = secrets.token_urlsafe(16)
    key = _lock_key(name)
    deadline = time.monotonic() + wait_seconds

    while True:
        try:
            if await client.set(key, token, nx=True, ex=ttl_seconds):
                return token
        except Exception:
            logger.debug("Lock acquire failed for '%s'", name, exc_info=True)
            return None

        if time.monotonic() >= deadline:
            return None
        await asyncio.sleep(poll_interval)


@asynccontextmanager
async def distributed_lock(
    name: str,
    *,
    ttl_seconds: int = 30,
    wait_seconds: float = 10.0,
) -> AsyncIterator[LockState]:
    """Yield lock state for a Redis-backed distributed lock."""
    client = await get_async_redis_client()
    if client is None:
        yield "no_redis"
        return

    token = await _acquire_lock_async(
        client, name, ttl_seconds=ttl_seconds, wait_seconds=wait_seconds
    )
    if token is None:
        yield "timeout"
        return

    try:
        yield "held"
    finally:
        try:
            await client.eval(_RELEASE_LOCK_LUA, 1, _lock_key(name), token)
        except Exception:
            logger.debug("Lock release failed for '%s'", name, exc_info=True)
