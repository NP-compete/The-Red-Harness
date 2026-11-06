"""Consent given once for a plan, spent step by step."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    """One step of a plan, and whether it writes."""

    tool: str
    writes: bool


class PlanConsent:
    """Consent given once for a plan, spent as its steps run."""

    def __init__(self, steps: list[Step]) -> None:
        """Bind to `steps`, with nothing yet approved."""
        if not steps:
            raise ValueError("a plan needs at least one step")
        self._steps = list(steps)
        self._allowance: Counter[str] = Counter()

    @property
    def acting_steps(self) -> list[Step]:
        """The steps of the plan that write."""
        return [step for step in self._steps if step.writes]

    def approve(self, *, acting: bool = True) -> None:
        """Grant one approval per acting step, or none if `acting` is false."""
        self._allowance = (
            Counter(step.tool for step in self.acting_steps) if acting else Counter()
        )

    def revoke(self) -> None:
        """Withdraw every remaining approval."""
        self._allowance = Counter()

    def use_for(self, step: Step) -> bool:
        """Spend one approval for this step; False when none is left."""
        if not step.writes:
            return True
        if self._allowance[step.tool] <= 0:
            return False
        self._allowance[step.tool] -= 1
        return True
