"""Token counts, in money."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable, Protocol


class Pricer(Protocol):
    """Prices one model's token usage."""

    def __call__(
        self, model: str, *, input_tokens: int, output_tokens: int
    ) -> dict[str, Any]:
        """What this many input and output tokens cost on `model`."""
        ...


def priced_usage(
    rows: list[dict[str, Any]],
    *,
    price: Pricer | Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Per-model usage with a cost against each, where one can be had."""
    out: list[dict[str, Any]] = []
    unpriced: list[str] = []
    total = Decimal("0")
    priced_any = False
    version = ""
    currency = ""

    for row in rows:
        model = str(row.get("model") or "")
        quoted = price(
            model,
            input_tokens=int(row.get("input_tokens") or 0),
            output_tokens=int(row.get("output_tokens") or 0),
        )
        version = version or str(quoted.get("rate_card_version") or "")
        currency = currency or str(quoted.get("currency") or "")

        cost = quoted.get("cost")
        if cost is None:
            unpriced.extend(quoted.get("unpriced") or [model])
        else:
            priced_any = True
            total += Decimal(str(cost))

        out.append({**row, "cost": cost})

    return {
        "rows": out,
        "total": _plain(total) if priced_any else None,
        "complete": priced_any and not unpriced,
        "unpriced": sorted(set(unpriced)),
        "rate_card_version": version,
        "currency": currency,
    }


def _plain(value: Decimal) -> str:
    """The amount, without exponent notation."""
    return format(value.normalize(), "f")
