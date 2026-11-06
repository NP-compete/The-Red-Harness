"""A record of every authorisation decision."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from agent.src.security.resolver import RefusalCode, Trust

Outcome = Literal["allowed", "needs_approval", "refused", "unavailable"]


@dataclass(frozen=True)
class Entry:
    """One recorded authorisation decision."""

    subject: str
    tool: str
    outcome: Outcome
    trust: Trust
    config_fingerprint: str
    schema_version: int
    resolver_version: str
    code: RefusalCode | None = None
    dependency: str | None = None


class DecisionJournal:
    """Every authorisation decision reached, in order."""

    def __init__(self) -> None:
        """Start an empty journal."""
        self._entries: list[Entry] = []

    @property
    def entries(self) -> tuple[Entry, ...]:
        """Every recorded entry, in order."""
        return tuple(self._entries)

    def record(self, entry: Entry) -> None:
        """Append one entry."""
        self._entries.append(entry)


@dataclass(frozen=True)
class Summary:
    """Counts and rates over a journal's decisions."""

    total: int
    allowed: int
    asked: int
    refused: int
    unavailable: int
    ask_rate: float
    refusals_by_code: dict[RefusalCode, int]
    asked_most: tuple[str, int] | None
    ever_untrusted: bool


def summarise(journal: "DecisionJournal") -> Summary:
    """Summarise the decisions in `journal`."""
    entries = journal.entries
    counts = Counter(entry.outcome for entry in entries)
    asked = counts["needs_approval"]

    asks_per_tool = Counter(
        entry.tool for entry in entries if entry.outcome == "needs_approval"
    )
    top = asks_per_tool.most_common(1)

    return Summary(
        total=len(entries),
        allowed=counts["allowed"],
        asked=asked,
        refused=counts["refused"],
        unavailable=counts["unavailable"],
        ask_rate=asked / len(entries) if entries else 0.0,
        refusals_by_code=Counter(
            entry.code for entry in entries if entry.code is not None
        ),
        asked_most=top[0] if top else None,
        ever_untrusted=any(entry.trust is Trust.UNTRUSTED_READ for entry in entries),
    )
