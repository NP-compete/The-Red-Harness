"""What is worth interrupting somebody about."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class Thresholds:
    """What this deployment asked to be told about."""

    error_rate: float | None = None
    p95_seconds: float | None = None
    spend: str | None = None


@dataclass(frozen=True)
class Breach:
    """One threshold that has been crossed, and the figures saying so."""

    name: str
    detail: str


def breaches(window: dict[str, Any], limits: Thresholds) -> list[Breach]:
    """Everything over its line, with the figures that say so."""
    found: list[Breach] = []

    rate = _error_rate(window)
    if limits.error_rate is not None and rate is not None and rate > limits.error_rate:
        found.append(
            Breach(
                "error_rate",
                f"{rate:.0%} of runs failed, over the {limits.error_rate:.0%} limit",
            )
        )

    p95 = window.get("p95_seconds")
    if limits.p95_seconds is not None and p95 is not None and p95 > limits.p95_seconds:
        found.append(
            Breach(
                "p95_seconds",
                f"95th percentile {p95:.0f}s, over the {limits.p95_seconds:.0f}s limit",
            )
        )

    spent = _amount(window.get("total_cost"))
    ceiling = _amount(limits.spend)
    if ceiling is not None and spent is not None and spent > ceiling:
        found.append(Breach("spend", f"{spent} spent, over the {ceiling} limit"))

    return found


def _error_rate(window: dict[str, Any]) -> float | None:
    """Failures as a share of runs, or nothing."""
    runs = int(window.get("runs") or 0)
    if runs <= 0:
        return None
    return int(window.get("errors") or 0) / runs


def _amount(value: Any) -> Decimal | None:
    """`value` as a decimal, or `None` if it is not one."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def from_config(raw: Any) -> Thresholds:
    """The limits a deployment configured, ignoring anything unusable."""
    alerts = (raw or {}).get("alerts") or {} if isinstance(raw, dict) else {}
    return Thresholds(
        error_rate=_positive(alerts.get("error_rate")),
        p95_seconds=_positive(alerts.get("p95_seconds")),
        spend=_money(alerts.get("spend")),
    )


def _positive(value: Any) -> float | None:
    """`value` as a float if it is above zero, otherwise `None`."""
    try:
        found = float(value)
    except (TypeError, ValueError):
        return None
    return found if found > 0 else None


def _money(value: Any) -> str | None:
    """Kept as written: through a float it stops being that number."""
    amount = _amount(value)
    return str(value) if amount is not None and amount > 0 else None
