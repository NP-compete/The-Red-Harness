"""Whether a conversation may be studied to improve the system."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

CLASSIFICATIONS = {"public", "internal", "confidential", "restricted"}


class Refusal(Enum):
    """Why a conversation may not be used for training."""

    LEGAL_HOLD = "legal-hold"
    CLASSIFICATION = "classification"
    SHARED_EXTERNALLY = "shared-externally"
    ORG_FORBIDS = "org-forbids"
    NO_CONSENT = "no-consent"
    NEEDS_SCRUBBING = "needs-scrubbing"


@dataclass(frozen=True)
class Settings:
    """What the org and the person have said about training."""

    org_allows: bool
    user_opted_in: bool
    requires_opt_in: bool = True


@dataclass(frozen=True)
class Conversation:
    """The facts about a conversation that bear on training use."""

    thread: str
    contains_personal_data: bool = False
    on_legal_hold: bool = False
    shared_externally: bool = False
    classification: str = "internal"

    def __post_init__(self) -> None:
        """Reject a conversation with no thread or an unknown classification."""
        if not self.thread.strip():
            raise ValueError("a conversation must have a thread")
        if self.classification not in CLASSIFICATIONS:
            raise ValueError(f"{self.classification} is not a classification")


@dataclass(frozen=True)
class Decision:
    """Whether a conversation may be used for training, and why not."""

    permitted: bool
    refusal: Refusal | None = None
    reason: str = ""


def may_use(
    conversation: Conversation, settings: Settings, *, scrubbed: bool = False
) -> Decision:
    """Decide whether `conversation` may be used for training."""

    def refuse(refusal: Refusal, reason: str) -> Decision:
        """A refusal with this code and reason."""
        return Decision(False, refusal, reason)

    if conversation.on_legal_hold:
        return refuse(Refusal.LEGAL_HOLD, "this conversation is under a legal hold")

    if conversation.classification == "restricted":
        return refuse(
            Refusal.CLASSIFICATION, "restricted conversations are never studied"
        )

    if conversation.shared_externally:
        return refuse(
            Refusal.SHARED_EXTERNALLY,
            "this conversation has been shared outside the organisation",
        )

    if not settings.org_allows:
        return refuse(Refusal.ORG_FORBIDS, "this organisation does not allow it")

    if settings.requires_opt_in and not settings.user_opted_in:
        return refuse(Refusal.NO_CONSENT, "nobody has agreed to this being used")

    if conversation.contains_personal_data and not scrubbed:
        return refuse(
            Refusal.NEEDS_SCRUBBING,
            "personal data would have to be removed first",
        )

    return Decision(True)
