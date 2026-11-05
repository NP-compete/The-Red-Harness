"""What one caller may spend before it is somebody else's turn."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

_TOMORROW_ISH = 3600.0


@dataclass(frozen=True)
class Limits:
    """What one caller is allowed. `None` for a cap means no cap."""

    per_second: float
    burst: int
    daily_spend: Decimal | None

    def __post_init__(self) -> None:
        """Reject limits that allow nothing, or a negative spend cap."""
        if self.per_second <= 0:
            raise ValueError("a rate of no calls per second allows nothing")
        if self.burst < 1:
            raise ValueError("a burst must allow at least one call")
        if self.daily_spend is not None and self.daily_spend < 0:
            raise ValueError("a spend cap below zero refuses everything, confusingly")


@dataclass(frozen=True)
class Admission:
    """Whether an inbound call is admitted, and when to try again."""

    allowed: bool
    reason: str = ""
    retry_after: float = 0.0


def admit(
    caller: str,
    *,
    limits: Limits | None,
    rate_ok: bool,
    spent: Decimal,
    retry_after: float = 0.0,
) -> Admission:
    """Whether this caller may start work right now."""
    if limits is None:
        return Admission(allowed=True)

    if not caller:
        return Admission(
            allowed=False,
            reason="inbound limits are on and this caller could not be identified",
        )

    cap = limits.daily_spend
    if cap is not None and spent >= cap:
        return Admission(
            allowed=False,
            reason=(
                f"this caller has spent {spent} today, at or over its "
                f"daily spend cap of {cap}"
            ),
            retry_after=_TOMORROW_ISH,
        )

    if not rate_ok:
        return Admission(
            allowed=False,
            reason=f"over the rate limit of {limits.per_second:g} calls per second",
            retry_after=retry_after,
        )

    return Admission(allowed=True)
