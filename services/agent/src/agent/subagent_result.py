"""Taking back what a subagent produced."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class Verdict(Enum):
    """What became of a subagent's answer."""

    ACCEPTED = "accepted"
    UNSOURCED = "unsourced"
    EMPTY = "empty"
    FAILED = "failed"


@dataclass(frozen=True)
class Returned:
    """What a subagent handed back, and what it cost."""

    child: str
    answer: str
    sources: tuple[str, ...]
    read_untrusted: bool
    cost: Decimal
    failed: bool
    reason: str

    def __post_init__(self) -> None:
        """Reject a negative cost, or a failure that does not say why."""
        if self.cost < 0:
            raise ValueError("a subagent cannot cost less than nothing")
        if self.failed and not self.reason.strip():
            raise ValueError("a failed subagent must say why")


@dataclass(frozen=True)
class Accepted:
    """The subagent's answer as taken up, and whether to retry."""

    verdict: Verdict
    answer: str
    sources: tuple[str, ...]
    cost: Decimal
    trusted: bool
    worth_retrying: bool
    reason: str = ""


def accept_result(returned: Returned) -> Accepted:
    """Decide what to do with what a subagent returned."""
    trusted = not returned.read_untrusted

    def result(
        verdict: Verdict, *, answer: str, worth_retrying: bool, reason: str = ""
    ) -> Accepted:
        """An outcome with this verdict and answer."""
        return Accepted(
            verdict=verdict,
            answer=answer,
            sources=returned.sources if answer else (),
            cost=returned.cost,
            trusted=trusted,
            worth_retrying=worth_retrying,
            reason=reason,
        )

    if returned.failed:
        return result(
            Verdict.FAILED, answer="", worth_retrying=True, reason=returned.reason
        )

    if not returned.answer.strip():
        return result(
            Verdict.EMPTY,
            answer="",
            worth_retrying=True,
            reason="the subagent returned nothing",
        )

    if not returned.sources:
        return result(
            Verdict.UNSOURCED,
            answer=returned.answer,
            worth_retrying=False,
            reason="this answer cites nothing",
        )

    return result(Verdict.ACCEPTED, answer=returned.answer, worth_retrying=False)
