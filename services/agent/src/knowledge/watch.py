"""Whether a change to a watched source is worth telling anyone about."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Change:
    """One edit to a watched document."""

    document: str
    words_changed: int
    sections_touched: tuple[str, ...]
    whitespace_only: bool
    deleted: bool
    by: str

    def __post_init__(self) -> None:
        """Reject a change smaller than nothing."""
        if self.words_changed < 0:
            raise ValueError("a change cannot be smaller than nothing")


@dataclass(frozen=True)
class Watch:
    """Someone's standing interest in a document, or parts of it."""

    watcher: str
    document: str
    sections: tuple[str, ...]
    minimum_words: int

    def __post_init__(self) -> None:
        """Reject a watch on nothing."""
        if not self.document.strip():
            raise ValueError("a watch must be on something")


@dataclass(frozen=True)
class Told:
    """Whether to tell the watcher, and what to say."""

    tell: bool
    summary: str


def _summarise(change: Change) -> str:
    """A one-line summary of a change."""
    if change.deleted:
        return f"{change.document} was deleted"
    if change.sections_touched:
        return f"{change.document} changed in {', '.join(change.sections_touched)}"
    return f"{change.document} changed"


def worth_telling(change: Change, *, watch: Watch) -> Told:
    """Decide whether `change` is worth telling the watcher about."""
    quiet = Told(tell=False, summary="")

    if change.document != watch.document:
        return quiet
    if change.by == watch.watcher:
        return quiet

    if change.deleted:
        return Told(tell=True, summary=_summarise(change))

    if change.whitespace_only or change.words_changed < watch.minimum_words:
        return quiet
    if watch.sections and not set(watch.sections) & set(change.sections_touched):
        return quiet

    return Told(tell=True, summary=_summarise(change))
