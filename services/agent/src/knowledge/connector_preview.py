"""What connecting a source would let the agent read."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Offer:
    """What a connector would reach if it were granted."""

    source: str
    folders: tuple[str, ...]
    documents: int
    includes_shared_with_you: bool
    includes_everything: bool
    writes: tuple[str, ...]
    reads_as: str

    def __post_init__(self) -> None:
        """Reject a negative document count, or an offer covering nothing."""
        if self.documents < 0:
            raise ValueError("a source cannot hold less than nothing")
        if not self.folders and not self.includes_everything:
            raise ValueError("an offer must cover something")


@dataclass(frozen=True)
class Preview:
    """What the connector would actually do, said plainly."""

    reads: list[str]
    documents: int
    acts_as: str
    warnings: list[str]
    read_only: bool

    @property
    def needs_careful_consent(self) -> bool:
        """Whether anything here warrants a careful read before consenting."""
        return bool(self.warnings)


def preview(offer: Offer) -> Preview:
    """Describe `offer` in terms the person can consent to."""
    warnings = []
    if offer.includes_everything:
        warnings.append("this covers everything in the account, not a chosen folder")
    if offer.includes_shared_with_you:
        warnings.append("this includes documents other people shared with you")
    if offer.writes:
        warnings.append(f"this can also {', '.join(offer.writes)}")

    return Preview(
        reads=["everything you can open"]
        if offer.includes_everything
        else list(offer.folders),
        documents=offer.documents,
        acts_as=offer.reads_as,
        warnings=warnings,
        read_only=not offer.writes,
    )
