"""What a run cost, at the rates that applied when it ran."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

_THOUSAND = Decimal(1000)


@dataclass(frozen=True)
class ModelRate:
    """What one model costs per thousand input and output tokens."""

    input_per_1k: str
    output_per_1k: str

    def price(self, input_tokens: int, output_tokens: int) -> Decimal:
        """What this many input and output tokens cost at this rate."""
        return (
            Decimal(self.input_per_1k) * Decimal(input_tokens) / _THOUSAND
            + Decimal(self.output_per_1k) * Decimal(output_tokens) / _THOUSAND
        )


@dataclass(frozen=True)
class RateCard:
    """A versioned set of per-model rates."""

    version: str
    rates: dict[str, ModelRate] = field(default_factory=dict)

    def price(
        self, model: str, *, input_tokens: int, output_tokens: int
    ) -> Decimal | None:
        """What a call to `model` costs, or `None` if the model is not priced."""
        rate = self.rates.get(model)
        if rate is None:
            return None
        return rate.price(input_tokens, output_tokens)


class RunCost:
    """Running total of what a single run has cost."""

    def __init__(self, card: RateCard, limit: Decimal | None = None) -> None:
        """Start an empty total against `card`, optionally capped at `limit`."""
        self._card = card
        self._limit = limit
        self._by_model: dict[str, Decimal] = {}
        self._unpriced: list[str] = []

    @property
    def rate_card_version(self) -> str:
        """The version of the rate card these totals were priced with."""
        return self._card.version

    @property
    def by_model(self) -> dict[str, Decimal]:
        """What has been spent so far, per model."""
        return dict(self._by_model)

    @property
    def total(self) -> Decimal:
        """What has been spent so far, across all models."""
        return sum(self._by_model.values(), Decimal("0"))

    @property
    def unpriced(self) -> tuple[str, ...]:
        """Models that were called but are not on the rate card."""
        return tuple(self._unpriced)

    @property
    def exceeded(self) -> bool:
        """Whether the total has gone past the limit."""
        return self._limit is not None and self.total > self._limit

    def record(self, model: str, *, input_tokens: int, output_tokens: int) -> None:
        """Add the cost of one call to the running total."""
        priced = self._card.price(
            model, input_tokens=input_tokens, output_tokens=output_tokens
        )
        if priced is None:
            self._unpriced.append(model)
            return
        self._by_model[model] = self._by_model.get(model, Decimal("0")) + priced
