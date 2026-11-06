"""Settling a request that is waiting for a person to decide."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Outcome(Enum):
    """How an approval request ended."""

    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    REFUSED = "refused"


@dataclass(frozen=True)
class ApprovalRequest:
    """A pending request for approval, and who may answer it."""

    tool: str
    requested_by: str
    requested_at: datetime
    expires_at: datetime
    eligible_approvers: tuple[str, ...]
    self_approval_allowed: bool = False

    def __post_init__(self) -> None:
        """Reject a request missing its tool or asker, or open for no time."""
        if not self.tool.strip():
            raise ValueError("an approval request must name the tool")
        if not self.requested_by.strip():
            raise ValueError("an approval request must name who asked")
        if self.expires_at <= self.requested_at:
            raise ValueError("an approval request must stay open for some time")


@dataclass(frozen=True)
class Settlement:
    """How a request was settled, by whom, and after how long."""

    outcome: Outcome
    permitted: bool
    reason: str
    decided_by: str
    waited_seconds: float


def settle(
    request: ApprovalRequest, *, approver: str, approved: bool, now: datetime
) -> Settlement:
    """Settle `request` with `approver`'s answer as of `now`."""

    def result(
        outcome: Outcome, reason: str = "", waited: float | None = None
    ) -> Settlement:
        """A settlement with this outcome and reason."""
        return Settlement(
            outcome=outcome,
            permitted=outcome is Outcome.APPROVED,
            reason=reason,
            decided_by=approver,
            waited_seconds=(now - request.requested_at).total_seconds()
            if waited is None
            else waited,
        )

    if now >= request.expires_at:
        open_for = (request.expires_at - request.requested_at).total_seconds()
        return result(
            Outcome.EXPIRED,
            f"nobody answered within {_minutes(open_for)}, so the call did not go ahead",
            waited=open_for,
        )

    if not request.eligible_approvers:
        return result(Outcome.REFUSED, "nobody is able to approve this request")

    is_requester = approver == request.requested_by

    if is_requester and not approved:
        return result(Outcome.DENIED)

    if is_requester and not request.self_approval_allowed:
        return result(Outcome.REFUSED, "you cannot approve your own request")

    if approver not in request.eligible_approvers:
        return result(
            Outcome.REFUSED, f"{approver} is not one of the approvers for this request"
        )

    return result(Outcome.APPROVED if approved else Outcome.DENIED)


def _minutes(seconds: float) -> str:
    """`seconds` rendered as whole minutes."""
    count = int(round(seconds / 60))
    return f"{count} minute{'' if count == 1 else 's'}"
