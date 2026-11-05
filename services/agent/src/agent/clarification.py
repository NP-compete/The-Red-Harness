"""Deciding whether to ask a question rather than guess at what was meant."""

from __future__ import annotations

from dataclasses import dataclass

CLEAR_ENOUGH = 0.9
MAX_ASKS = 2


@dataclass(frozen=True)
class Ambiguity:
    """One thing in a request that could be read more than one way."""

    about: str
    options: tuple[str, ...]
    confidence: float

    def __post_init__(self) -> None:
        """Reject a single reading, or confidence outside zero to one."""
        if len(self.options) < 2:
            raise ValueError("something with one reading is not ambiguous")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence runs from nothing to certainty")


@dataclass(frozen=True)
class Request:
    """What is ambiguous, and how much room there is to ask."""

    ambiguities: tuple[Ambiguity, ...]
    reversible: bool
    unattended: bool
    attempts_so_far: int


@dataclass(frozen=True)
class Decision:
    """Whether to ask, what to ask, or what to assume instead."""

    ask: bool
    stop: bool = False
    question: str = ""
    options: tuple[str, ...] = ()
    assuming: str = ""
    reason: str = ""


def should_ask(request: Request) -> Decision:
    """Decide whether to ask about `request` or press on with an assumption."""
    if not request.ambiguities:
        return Decision(ask=False)

    worst = min(request.ambiguities, key=lambda item: item.confidence)
    likely = worst.options[0]

    if worst.confidence >= CLEAR_ENOUGH and request.reversible:
        return Decision(ask=False, assuming=likely)

    if request.unattended:
        return Decision(
            ask=False,
            stop=True,
            assuming="",
            reason=f"nobody is here to say {worst.about}",
        )

    if request.attempts_so_far >= MAX_ASKS:
        return Decision(
            ask=False,
            assuming=likely,
            reason="this has been asked already, so the likeliest reading is used",
        )

    return Decision(
        ask=True,
        question=f"{worst.about}: {' or '.join(worst.options)}?",
        options=worst.options,
    )
