"""Checking that each claim in an answer appears in what was actually read."""

from __future__ import annotations

import re
from dataclasses import dataclass

OVERLAP_NEEDED = 0.6

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "to",
    "of",
    "and",
    "or",
    "in",
    "on",
    "for",
    "with",
    "that",
    "this",
    "it",
    "its",
    "as",
}

NEGATIONS = {"not", "no", "never", "cannot", "nor", "without", "neither", "nothing"}

OPPOSITES = {
    "over": "under",
    "under": "over",
    "above": "below",
    "below": "above",
    "more": "less",
    "less": "more",
    "before": "after",
    "after": "before",
    "all": "some",
    "every": "some",
    "some": "all",
    "most": "few",
    "few": "most",
}

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")

_WORD = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Passage:
    """One retrieved passage an answer may cite."""

    source: str
    text: str

    def __post_init__(self) -> None:
        """Reject a passage that does not say where it came from."""
        if not self.source.strip():
            raise ValueError("a passage must say where it came from")


@dataclass(frozen=True)
class Claim:
    """One claim in an answer, and the passages it cites."""

    text: str
    cites: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a claim that says nothing."""
        if not self.text.strip():
            raise ValueError("a claim must say something")


@dataclass(frozen=True)
class CheckedClaim:
    """One claim after checking it against the passages it cites."""

    text: str
    supported: bool
    supported_by: str = ""
    contradicted: bool = False
    reason: str = ""


@dataclass(frozen=True)
class Support:
    """How well an answer's claims are grounded in its passages."""

    claims: tuple[CheckedClaim, ...]
    grounded: bool
    supported_share: float
    unsupported: tuple[str, ...]
    contradicted: tuple[str, ...] = ()
    reason: str = ""


def check_support(claims: list[Claim], *, passages: tuple[Passage, ...]) -> Support:
    """Check every claim against the passages and report how grounded it is."""
    if not passages:
        raise ValueError("there is nothing to check the answer against")

    by_source = {passage.source: passage for passage in passages}
    checked = tuple(_check(claim, by_source) for claim in claims)

    supported = [claim for claim in checked if claim.supported]

    return Support(
        claims=checked,
        grounded=bool(checked) and len(supported) == len(checked),
        supported_share=len(supported) / len(checked) if checked else 0.0,
        unsupported=tuple(claim.text for claim in checked if not claim.supported),
        contradicted=tuple(claim.text for claim in checked if claim.contradicted),
        reason="" if checked else "there was nothing in the answer to check",
    )


def _check(claim: Claim, by_source: dict[str, Passage]) -> CheckedClaim:
    """Check one claim against the passages it cites."""
    if not claim.cites:
        return CheckedClaim(
            claim.text, supported=False, reason="this claim gives no source"
        )

    missing = [name for name in claim.cites if name not in by_source]
    if len(missing) == len(claim.cites):
        return CheckedClaim(
            claim.text,
            supported=False,
            reason=f"{', '.join(missing)} was not among the passages read",
        )

    wanted = _words(claim.text)
    for name in claim.cites:
        passage = by_source.get(name)
        if passage is None:
            continue
        found = wanted & _words(passage.text)
        if not wanted or len(found) / len(wanted) < OVERLAP_NEEDED:
            continue
        invented = _numbers(claim.text) - _numbers(passage.text)
        if invented:
            return CheckedClaim(
                claim.text,
                supported=False,
                reason=f"{name} does not mention {', '.join(sorted(invented))}",
            )
        if _flips(claim.text, passage.text):
            return CheckedClaim(
                claim.text,
                supported=False,
                contradicted=True,
                reason=f"{name} says the opposite",
            )
        if _is_negative(claim.text) != _is_negative(passage.text):
            return CheckedClaim(
                claim.text,
                supported=False,
                contradicted=True,
                reason=f"{name} says otherwise",
            )
        return CheckedClaim(claim.text, supported=True, supported_by=name)

    return CheckedClaim(
        claim.text,
        supported=False,
        reason="the cited passages do not say this",
    )


def _words(text: str) -> set[str]:
    """The meaningful words of `text`, lowercased."""
    return {
        word
        for word in _WORD.findall(text.lower())
        if word not in STOPWORDS and word not in NEGATIONS
    }


def _is_negative(text: str) -> bool:
    """Whether `text` carries an odd number of negations."""
    lowered = text.lower().replace("n't", " not ")
    return sum(1 for word in _WORD.findall(lowered) if word in NEGATIONS) % 2 == 1


def _numbers(text: str) -> set[str]:
    """Every number appearing in `text`."""
    return set(_NUMBER.findall(text))


def _flips(claim: str, passage: str) -> bool:
    """Whether the claim uses a word whose opposite is what the passage says."""
    claim_words = set(_WORD.findall(claim.lower()))
    passage_words = set(_WORD.findall(passage.lower()))
    return any(
        word in claim_words
        and OPPOSITES[word] in passage_words
        and word not in passage_words
        for word in OPPOSITES
    )
