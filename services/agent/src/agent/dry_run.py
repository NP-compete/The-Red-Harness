"""Showing what a run would do, before it does any of it."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

PENNY = Decimal("0.01")


@dataclass(frozen=True)
class Intent:
    """One thing a run means to do, and what it would cost."""

    tool: str
    target: str
    writes: bool
    reversible: bool
    needs_approval: bool
    estimated_cost: Decimal

    def __post_init__(self) -> None:
        """Reject an intent with no tool, no target, or a negative estimate."""
        if not self.tool.strip():
            raise ValueError("an intent must name a tool")
        if not self.target.strip():
            raise ValueError("an intent must name what it acts on")
        if self.estimated_cost < 0:
            raise ValueError("an estimate cannot be below nothing")


@dataclass(frozen=True)
class Step:
    """One step as it would appear in a preview."""

    tool: str
    target: str
    harmless: bool


@dataclass(frozen=True)
class Preview:
    """What a run would do if it were let go."""

    steps: tuple[Step, ...]
    executed: bool
    would_change: int
    estimated_cost: Decimal
    needs_approval: tuple[str, ...]
    permanent: tuple[str, ...]
    runnable: bool
    summary: str
    reason: str = ""


def preview(intents: list[Intent]) -> Preview:
    """Describe what `intents` would do, without doing any of it."""
    if not intents:
        raise ValueError("there is nothing to preview")

    writes = [intent for intent in intents if intent.writes]
    reads = len(intents) - len(writes)
    approvals = tuple(
        f"{intent.tool}: {intent.target}" for intent in intents if intent.needs_approval
    )

    cost = sum((intent.estimated_cost for intent in intents), Decimal("0")).quantize(
        PENNY, rounding=ROUND_HALF_UP
    )

    return Preview(
        steps=tuple(
            Step(tool=intent.tool, target=intent.target, harmless=not intent.writes)
            for intent in intents
        ),
        executed=False,
        would_change=len(writes),
        estimated_cost=cost,
        needs_approval=approvals,
        permanent=tuple(
            f"{intent.tool}: {intent.target}"
            for intent in intents
            if intent.writes and not intent.reversible
        ),
        runnable=not approvals,
        summary=_summarise(len(writes), reads, cost),
        reason="some steps need approval before this can run" if approvals else "",
    )


def _summarise(changes: int, reads: int, cost: Decimal) -> str:
    """The one-line summary of a preview."""
    if changes == 0:
        return "nothing would change"
    parts = [f"{changes} change{'' if changes == 1 else 's'}"]
    if reads:
        parts.append(f"{reads} read{'' if reads == 1 else 's'}")
    parts.append(f"about {cost}")
    return ", ".join(parts)
