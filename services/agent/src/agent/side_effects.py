"""What a run changed outside itself, and what can be put back."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

PENNY = Decimal("0.01")


@dataclass(frozen=True)
class Effect:
    """One thing a run changed, and whether it can be put back."""

    kind: str
    target: str
    reversible: bool
    undo_hint: str
    cost: Decimal

    def __post_init__(self) -> None:
        """Reject an effect with no target, negative cost, or no undo hint."""
        if not self.target.strip():
            raise ValueError("an effect must say what it touched")
        if self.cost < 0:
            raise ValueError("an effect cannot cost less than nothing")
        if self.reversible and not self.undo_hint.strip():
            raise ValueError("something reversible must say how to reverse it")


@dataclass(frozen=True)
class Effects:
    """Everything a run changed, grouped, and what cannot be undone."""

    count: int
    changed_anything: bool
    by_kind: dict[str, tuple[str, ...]]
    permanent: tuple[str, ...]
    fully_reversible: bool
    undo_steps: tuple[str, ...]
    cost: Decimal
    summary: str


def summarise_effects(effects: list[Effect]) -> Effects:
    """Summarise `effects`, folding away repeats."""
    unique = list({(effect.kind, effect.target): effect for effect in effects}.values())

    by_kind: dict[str, list[str]] = {}
    for effect in unique:
        by_kind.setdefault(effect.kind, []).append(effect.target)

    permanent = tuple(
        f"{effect.kind}: {effect.target}" for effect in unique if not effect.reversible
    )

    return Effects(
        count=len(unique),
        changed_anything=bool(unique),
        by_kind={kind: tuple(sorted(targets)) for kind, targets in by_kind.items()},
        permanent=permanent,
        fully_reversible=not permanent,
        undo_steps=tuple(
            dict.fromkeys(effect.undo_hint for effect in unique if effect.reversible)
        ),
        cost=sum((effect.cost for effect in unique), Decimal("0")).quantize(
            PENNY, rounding=ROUND_HALF_UP
        ),
        summary=_summarise(by_kind),
    )


def _summarise(by_kind: dict[str, list[str]]) -> str:
    """The one-line summary of what changed."""
    if not by_kind:
        return "Nothing was changed"

    parts = []
    for kind, targets in sorted(
        by_kind.items(), key=lambda item: (-len(item[1]), item[0])
    ):
        noun, _, verb = kind.partition("-")
        count = len(targets)
        parts.append(f"{count} {noun if count == 1 else noun + 's'} {verb}")
    return ", ".join(parts)
