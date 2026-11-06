"""Fitting what the model needs to know into the room available."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    """One part that could go into the context, and what it costs."""

    name: str
    tokens: int
    priority: int
    required: bool = False

    def __post_init__(self) -> None:
        """Reject a nameless or empty part."""
        if not self.name.strip():
            raise ValueError("a part must have a name")
        if self.tokens < 1:
            raise ValueError("a part with nothing in it is not a part")


@dataclass(frozen=True)
class Allocation:
    """What went into the context, what was dropped, and what is spare."""

    included: tuple[Candidate, ...]
    dropped: tuple[str, ...]
    used_tokens: int
    spare_tokens: int
    over_budget: bool


def allocate(candidates: list[Candidate], *, budget_tokens: int) -> Allocation:
    """Fit as much of `candidates` into `budget_tokens` as priority allows."""
    if budget_tokens < 1:
        raise ValueError("there must be room for something")

    priorities = [part.priority for part in candidates]
    if len(priorities) != len(set(priorities)):
        raise ValueError("two parts cannot have the same priority")

    required = [part for part in candidates if part.required]
    used = sum(part.tokens for part in required)
    kept = {part.name for part in required}

    for part in sorted(
        (part for part in candidates if not part.required),
        key=lambda part: part.priority,
    ):
        if used + part.tokens <= budget_tokens:
            kept.add(part.name)
            used += part.tokens

    return Allocation(
        included=tuple(part for part in candidates if part.name in kept),
        dropped=tuple(part.name for part in candidates if part.name not in kept),
        used_tokens=used,
        spare_tokens=max(0, budget_tokens - used),
        over_budget=used > budget_tokens,
    )
