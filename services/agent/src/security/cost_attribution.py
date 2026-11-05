"""Deciding which budget a run's cost lands on."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

PENNY = Decimal("0.01")
PLATFORM = "platform"
SCHEDULE = "schedule"


@dataclass(frozen=True)
class RunCost:
    """What one run cost, and who it was run by and for."""

    run_id: str
    person: str
    team: str
    project: str
    amount: Decimal
    subagent_amounts: dict[str, Decimal] = field(default_factory=dict)
    started_by: str = "person"
    space: str = ""

    def __post_init__(self) -> None:
        """Reject a negative cost, or a run attributable to nobody."""
        if self.amount < 0 or any(
            value < 0 for value in self.subagent_amounts.values()
        ):
            raise ValueError("a cost cannot be negative")
        if not (self.person.strip() or self.team.strip() or self.project.strip()):
            raise ValueError("a run must be attributable to someone")


@dataclass(frozen=True)
class Charge:
    """What a run is charged, and to whom."""

    run_id: str
    charged_to: str
    person: str
    amount: Decimal
    breakdown: dict[str, Decimal]
    space: str = ""


def attribute(run: RunCost) -> Charge:
    """Work out who `run` is charged to, and the breakdown."""
    breakdown = {"main": _money(run.amount)}
    for name, amount in run.subagent_amounts.items():
        breakdown[name] = _money(amount)

    return Charge(
        run_id=run.run_id,
        charged_to=_payer(run),
        person=run.person,
        amount=_money(sum(breakdown.values(), Decimal("0"))),
        breakdown=breakdown,
        space=run.space,
    )


def _payer(run: RunCost) -> str:
    """Who a run is charged to: project, team, or the platform."""
    if run.project.strip():
        return run.project
    if run.team.strip():
        return run.team
    if run.started_by == SCHEDULE:
        return PLATFORM
    return run.person


def _money(amount: Decimal) -> Decimal:
    """`amount` rounded to the penny."""
    return amount.quantize(PENNY, rounding=ROUND_HALF_UP)


_KEEP_SECONDS = 120 * 24 * 60 * 60


def month_of(day: str) -> str:
    """The billing period a day falls in."""
    return day[:7]


def _ledger_key(month: str) -> str:
    """The ledger key for a month's charges."""
    return f"charge:{month}"


def _count_key(month: str) -> str:
    """The key counting a month's runs."""
    return f"charge:{month}:runs"


def _unpriced_key(month: str) -> str:
    """Runs that happened and could not be priced."""
    return f"charge:{month}:unpriced"


def _space_key(month: str, space: str) -> str:
    """The ledger key for a space's charges in a month."""
    return f"charge:{month}:space:{space}"


def _space_count_key(month: str, space: str) -> str:
    """The key counting a space's runs in a month."""
    return f"charge:{month}:space:{space}:runs"


async def _client(client: Any) -> Any:
    """`client` if it was given, otherwise a Redis client."""
    if client is not None:
        return client
    from agent.aegra.redis import get_async_redis_client

    return await get_async_redis_client()


async def charge_for(
    run: RunCost, *, client: Any = None, month: str | None = None
) -> None:
    """Put a run's cost on whoever pays for it."""
    found = attribute(run)

    from datetime import datetime, timezone

    when = month or datetime.now(timezone.utc).strftime("%Y-%m")
    redis = await _client(client)

    if found.amount <= 0:
        try:
            await redis.incr(_unpriced_key(when))
            await redis.expire(_unpriced_key(when), _KEEP_SECONDS)
        except Exception as error:  # noqa: BLE001
            logger.warning("Could not count an unpriced run: %s", error)
        return
    try:
        await redis.hincrbyfloat(
            _ledger_key(when), found.charged_to, float(found.amount)
        )
        await redis.expire(_ledger_key(when), _KEEP_SECONDS)
        await redis.hincrbyfloat(_count_key(when), found.charged_to, 1)
        await redis.expire(_count_key(when), _KEEP_SECONDS)
    except Exception as error:
        logger.warning(
            "Could not charge %s to %s: %s", found.amount, found.charged_to, error
        )

    if not found.space.strip():
        return
    try:
        await redis.hincrbyfloat(
            _space_key(when, found.space), found.person, float(found.amount)
        )
        await redis.expire(_space_key(when, found.space), _KEEP_SECONDS)
        await redis.hincrbyfloat(_space_count_key(when, found.space), found.person, 1)
        await redis.expire(_space_count_key(when, found.space), _KEEP_SECONDS)
    except Exception as error:
        logger.warning(
            "Could not attribute %s to space %s: %s", found.amount, found.space, error
        )


async def unpriced_in(month: str, *, client: Any = None) -> int:
    """How many runs this month could not be priced."""
    redis = await _client(client)
    try:
        found = await redis.get(_unpriced_key(month))
    except Exception as error:  # noqa: BLE001
        logger.warning("Could not read the unpriced count for %s: %s", month, error)
        return 0
    if found is None:
        return 0
    try:
        return int(found.decode() if isinstance(found, bytes) else found)
    except (TypeError, ValueError):
        return 0


async def charges_in(month: str, *, client: Any = None) -> dict[str, dict[str, Any]]:
    """Every payer's total for a month, and how many runs made it."""
    redis = await _client(client)
    try:
        amounts = await redis.hgetall(_ledger_key(month))
        counts = await redis.hgetall(_count_key(month))
    except Exception as error:
        logger.warning("Could not read the charges for %s: %s", month, error)
        return {}

    return _rows(amounts, counts)


async def space_charges_in(
    space: str, month: str, *, client: Any = None
) -> dict[str, dict[str, Any]]:
    """What a room cost in a month, per person (E33-T5)."""
    redis = await _client(client)
    try:
        amounts = await redis.hgetall(_space_key(month, space))
        counts = await redis.hgetall(_space_count_key(month, space))
    except Exception as error:
        logger.warning("Could not read the charges for space %s: %s", space, error)
        return {}
    return _rows(amounts, counts)


def _rows(amounts: Any, counts: Any) -> dict[str, dict[str, Any]]:
    """The stored amounts and counts as one row per payer."""
    found: dict[str, dict[str, Any]] = {}
    for payer, raw in (amounts or {}).items():
        name = payer.decode() if isinstance(payer, bytes) else str(payer)
        try:
            amount = _money(
                Decimal(raw.decode() if isinstance(raw, bytes) else str(raw))
            )
        except (InvalidOperation, ValueError, AttributeError):
            logger.warning("The charge for %s is not an amount: %r", name, raw)
            continue
        found[name] = {"amount": amount, "runs": _count(counts, name)}
    return found


def _count(counts: Any, payer: str) -> int:
    """The run count stored for `payer`."""
    for key, raw in (counts or {}).items():
        name = key.decode() if isinstance(key, bytes) else str(key)
        if name != payer:
            continue
        try:
            return int(float(raw.decode() if isinstance(raw, bytes) else str(raw)))
        except (TypeError, ValueError):
            return 0
    return 0
