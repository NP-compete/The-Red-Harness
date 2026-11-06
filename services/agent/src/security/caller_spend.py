"""What a caller has spent today, counted where every pod sees it."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_KEEP_SECONDS = 2 * 24 * 60 * 60

_KEEP_MONTH_SECONDS = 70 * 24 * 60 * 60


def today() -> str:
    """The day the cap resets on, in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def this_month() -> str:
    """The month the forecast is made over, in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def key_for(caller: str, *, day: str) -> str:
    """The key a caller's spending for `day` is counted under."""
    return f"inbound:spend:{day}:{caller}"


def month_key_for(caller: str, *, month: str) -> str:
    """Separate from the day's key."""
    return f"inbound:spend:month:{month}:{caller}"


async def _client() -> Any:
    """An async Redis client."""
    from agent.aegra.redis import get_async_redis_client

    return await get_async_redis_client()


async def spent_today(
    caller: str, *, client: Any = None, day: str | None = None
) -> Decimal:
    """What this caller has spent today, or zero if it cannot be said."""
    if not caller:
        return Decimal("0")

    redis = client if client is not None else await _client()
    try:
        raw = await redis.get(key_for(caller, day=day or today()))
    except Exception as error:
        logger.warning("Could not read the spend counter for %s: %s", caller, error)
        return Decimal("0")

    if raw is None:
        return Decimal("0")

    try:
        return Decimal(raw.decode() if isinstance(raw, bytes) else str(raw))
    except (InvalidOperation, ValueError, AttributeError):
        logger.warning("The spend counter for %s is not an amount: %r", caller, raw)
        return Decimal("0")


async def spent_this_month(
    caller: str, *, client: Any = None, month: str | None = None
) -> Decimal:
    """What this caller has spent this month, or zero if it cannot be said."""
    if not caller:
        return Decimal("0")

    redis = client if client is not None else await _client()
    try:
        raw = await redis.get(month_key_for(caller, month=month or this_month()))
    except Exception as error:
        logger.warning("Could not read the monthly spend for %s: %s", caller, error)
        return Decimal("0")

    if raw is None:
        return Decimal("0")

    try:
        return Decimal(raw.decode() if isinstance(raw, bytes) else str(raw))
    except (InvalidOperation, ValueError, AttributeError):
        logger.warning("The monthly spend for %s is not an amount: %r", caller, raw)
        return Decimal("0")


async def record(
    caller: str, amount: Decimal, *, client: Any = None, day: str | None = None
) -> None:
    """Add what a run cost to this caller's day."""
    if not caller or amount <= 0:
        return

    when = day or today()
    redis = client if client is not None else await _client()
    counters = (
        (key_for(caller, day=when), _KEEP_SECONDS),
        (month_key_for(caller, month=when[:7]), _KEEP_MONTH_SECONDS),
    )
    for key, keep in counters:
        try:
            await redis.incrbyfloat(key, float(amount))
            await redis.expire(key, keep)
        except Exception as error:
            logger.warning(
                "Could not record spend for %s in %s: %s", caller, key, error
            )
