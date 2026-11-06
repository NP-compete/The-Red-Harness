"""Who can reach which agent, and whether they still need to."""

from __future__ import annotations

from dataclasses import dataclass

_DIRECT_NOTE = (
    "Granted directly rather than through a group, so nothing will revoke it."
)


@dataclass(frozen=True)
class Grant:
    """One standing grant of access, and when it was last used."""

    subject: str
    agent: str
    via: str
    last_used_days: int | None


@dataclass(frozen=True)
class ReviewRow:
    """One grant as it appears in the review, flagged or not."""

    subject: str
    agent: str
    via: str
    last_used_days: int | None
    flagged: bool
    note: str


@dataclass(frozen=True)
class Review:
    """Every grant up for review, and how many need attention."""

    rows: tuple[ReviewRow, ...]
    needing_attention: int
    service_accounts: int


def build_review(*, grants: list[Grant], stale_after_days: int) -> Review:
    """Build the access review, flagging grants unused for too long."""
    if stale_after_days <= 0:
        raise ValueError("a staleness window of nothing flags every grant")

    rows = [
        ReviewRow(
            subject=grant.subject,
            agent=grant.agent,
            via=grant.via,
            last_used_days=grant.last_used_days,
            flagged=grant.last_used_days is None
            or grant.last_used_days > stale_after_days,
            note=_DIRECT_NOTE if grant.via == "direct" else "",
        )
        for grant in grants
    ]

    rows.sort(key=lambda row: (not row.flagged, row.subject, row.agent))

    return Review(
        rows=tuple(rows),
        needing_attention=sum(1 for row in rows if row.flagged),
        service_accounts=sum(1 for row in rows if row.via == "service"),
    )
