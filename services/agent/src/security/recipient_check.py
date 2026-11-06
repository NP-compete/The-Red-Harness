"""Checking who an outgoing message would actually reach."""

from __future__ import annotations

from dataclasses import dataclass

CROWD = 20


@dataclass(frozen=True)
class Recipient:
    """One address a message would go to, and how far it reaches."""

    address: str
    inside: bool
    is_list: bool
    reaches: int
    known: bool

    def __post_init__(self) -> None:
        """Reject a recipient that reaches nobody."""
        if self.reaches < 1:
            raise ValueError("a recipient must reach someone")


@dataclass(frozen=True)
class Checked:
    """How far a message would reach, and what is worth confirming."""

    reaches: int
    outside: list[str]
    unfamiliar: list[str]
    reasons: list[str]

    @property
    def confirm(self) -> bool:
        """Whether anything found is worth confirming first."""
        return bool(self.reasons)


def check_recipients(recipients: list[Recipient]) -> Checked:
    """Work out how far a message to `recipients` would actually go."""
    if not recipients:
        raise ValueError("a message must be addressed to someone")

    unique: dict[str, Recipient] = {}
    for recipient in recipients:
        unique.setdefault(recipient.address, recipient)

    reaches = sum(recipient.reaches for recipient in unique.values())
    outside = [r.address for r in unique.values() if not r.inside]
    unfamiliar = [r.address for r in unique.values() if not r.known]

    reasons = []
    if outside:
        reasons.append("someone outside the organisation")
    if any(r.is_list for r in unique.values()):
        reasons.append("a mailing list")
    if reaches >= CROWD:
        reasons.append("more people than a message usually goes to")
    if unfamiliar:
        reasons.append("an address not written to before")

    return Checked(
        reaches=reaches, outside=outside, unfamiliar=unfamiliar, reasons=reasons
    )
