"""How plainly an answer should be stated, given what it rests on."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

ENOUGH_COVERAGE = 0.8
ENOUGH_SUPPORT = 0.5
STALE_DAYS = 365


class Stance(Enum):
    """How plainly an answer should be stated."""

    PLAIN = "plain"
    HEDGED = "hedged"
    DECLINE = "decline"


@dataclass(frozen=True)
class Signals:
    """What is known about how well an answer is grounded."""

    coverage: float
    claims_supported: float
    sources: int
    sources_disagree: bool
    oldest_source_days: int
    freshness_matters: bool
    built_on_untrusted: bool

    def __post_init__(self) -> None:
        """Reject coverage or support outside zero to one, or negative sources."""
        if not 0.0 <= self.coverage <= 1.0:
            raise ValueError("coverage runs from zero to one")
        if not 0.0 <= self.claims_supported <= 1.0:
            raise ValueError("support runs from zero to one")
        if self.sources < 0:
            raise ValueError("an answer cannot rest on fewer than no sources")


@dataclass(frozen=True)
class Stated:
    """The stance to take, the hedge to use, and what would help."""

    stance: Stance
    hedge: str
    concerns: list[str]
    what_would_help: str


def decide_stance(signals: Signals) -> Stated:
    """Decide how confidently an answer backed by `signals` should be put."""
    concerns = []
    if signals.coverage < ENOUGH_COVERAGE:
        concerns.append("this answers only part of what was asked")
    if signals.claims_supported < ENOUGH_SUPPORT:
        concerns.append("most of this is not backed by what was read")
    if signals.sources == 0:
        concerns.append("nothing was found to answer from")
    elif signals.sources == 1:
        concerns.append("this rests on a single source")
    if signals.sources_disagree:
        concerns.append("the sources disagree")
    if signals.freshness_matters and signals.oldest_source_days > STALE_DAYS:
        concerns.append("the sources are old and this may have moved on")
    if signals.built_on_untrusted:
        concerns.append("some of this came from material that cannot be vouched for")

    if signals.sources == 0 or signals.claims_supported < ENOUGH_SUPPORT:
        return Stated(
            stance=Stance.DECLINE,
            hedge="; ".join(concerns),
            concerns=concerns,
            what_would_help="a source that speaks to this question",
        )

    if concerns:
        return Stated(
            stance=Stance.HEDGED,
            hedge="; ".join(concerns),
            concerns=concerns,
            what_would_help="",
        )

    return Stated(stance=Stance.PLAIN, hedge="", concerns=[], what_would_help="")
