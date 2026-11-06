"""A ceiling on what one run may cost, and a word before it is reached."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


def _plain(amount: Decimal) -> str:
    """A fixed-point string: `2E-7` is not an amount anyone can check."""
    return format(amount, "f")


@dataclass(frozen=True)
class Verdict:
    """What to say about spending, and whether to stop the run."""

    message: str
    """Stop the run, rather than merely saying something about it."""
    refuse: bool


@dataclass
class SpendCap:
    """Tracks one run against its allowance."""

    warn_at: Decimal | None = None
    refuse_at: Decimal | None = None
    currency: str = ""
    _warned: bool = field(default=False, init=False, repr=False)

    def _money(self, amount: Decimal) -> str:
        """`amount` rendered with its currency."""
        return f"{_plain(amount)} {self.currency}".strip()

    def __post_init__(self) -> None:
        """Reject a cap that warns after it refuses."""
        if (
            self.warn_at is not None
            and self.refuse_at is not None
            and self.warn_at > self.refuse_at
        ):
            raise ValueError(
                f"warn_at ({self.warn_at}) is above refuse_at ({self.refuse_at}): "
                "the warning would never be seen before the refusal"
            )

    def check(self, spent: Decimal | None) -> Verdict | None:
        """What to do about a run that has spent this much so far."""
        if spent is None:
            return None

        if self.refuse_at is not None and spent >= self.refuse_at:
            return Verdict(
                message=(
                    f"This run has reached its spending limit of "
                    f"{self._money(self.refuse_at)} and was stopped at "
                    f"{self._money(spent)}. Ask again to start a new run, "
                    "or raise the limit."
                ),
                refuse=True,
            )

        if self.warn_at is not None and spent >= self.warn_at and not self._warned:
            self._warned = True
            return Verdict(
                message=(
                    f"This run has spent {self._money(spent)} of its "
                    f"{self._money(self.refuse_at)} limit."
                    if self.refuse_at is not None
                    else f"This run has spent {self._money(spent)}."
                ),
                refuse=False,
            )

        return None
