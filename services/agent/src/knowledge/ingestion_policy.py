"""Whether a document may be taken into the knowledge base."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

MAX_BYTES = 100_000_000
CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}
READABLE = {"document", "spreadsheet", "text", "image"}
COPYABLE = {"owned", "licensed", "public-domain"}


class Refusal(Enum):
    """Why a document may not be taken into the corpus."""

    NOT_SCANNED = "not-scanned"
    UNSAFE = "unsafe"
    CLASSIFICATION = "classification"
    LICENCE = "licence"
    PERSONAL_DATA = "personal-data"
    TOO_LARGE = "too-large"
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class Document:
    """A document offered for ingestion, and what is known about it."""

    name: str
    bytes: int
    kind: str
    classification: str
    licence: str
    contains_personal_data: bool
    scanned: bool
    safe: bool

    def __post_init__(self) -> None:
        """Reject a document with no name or an unknown classification."""
        if not self.name.strip():
            raise ValueError("a document must have a name")
        if self.classification not in CLASSIFICATIONS:
            raise ValueError(f"{self.classification} is not a classification")


@dataclass(frozen=True)
class Decision:
    """Whether a document may be ingested, and why not."""

    permitted: bool
    refusal: Refusal | None = None
    retry_after_scan: bool = False
    reason: str = ""


def may_ingest(document: Document, *, scrubbed: bool = False) -> Decision:
    """Decide whether `document` may be taken into the corpus."""

    def refuse(refusal: Refusal, reason: str, *, rescan: bool = False) -> Decision:
        """A refusal with this code and reason."""
        return Decision(False, refusal, retry_after_scan=rescan, reason=reason)

    if not document.scanned:
        return refuse(Refusal.NOT_SCANNED, "this has not been checked yet", rescan=True)
    if not document.safe:
        return refuse(Refusal.UNSAFE, "this did not pass its safety check")

    if document.classification == "restricted":
        return refuse(Refusal.CLASSIFICATION, "restricted material is never taken in")

    if document.licence not in COPYABLE:
        return refuse(Refusal.LICENCE, "this may not be copied into the knowledge base")

    if document.kind not in READABLE:
        return refuse(Refusal.UNREADABLE, f"a {document.kind} cannot be read as text")

    if document.bytes > MAX_BYTES:
        return refuse(Refusal.TOO_LARGE, "this is larger than can be taken in at once")

    if document.contains_personal_data and not scrubbed:
        return refuse(
            Refusal.PERSONAL_DATA,
            "scrub the personal data out and it can be taken in",
        )

    return Decision(True)
