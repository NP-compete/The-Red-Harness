"""How much a team may keep, and what happens as it fills up."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

NEARLY_FULL_AT = 0.8


class State(Enum):
    """How close a store is to its quota."""

    FINE = "fine"
    NEARLY_FULL = "nearly-full"
    FULL = "full"


@dataclass(frozen=True)
class Quota:
    """What a store holds, what it may hold, and what could be freed."""

    used_bytes: int
    limit_bytes: int
    incoming_bytes: int = 0
    oldest_removable_bytes: int = 0

    def __post_init__(self) -> None:
        """Reject a quota of nothing, or negative byte counts."""
        if self.limit_bytes < 1:
            raise ValueError("a quota must allow something to be stored")
        if (
            self.used_bytes < 0
            or self.incoming_bytes < 0
            or self.oldest_removable_bytes < 0
        ):
            raise ValueError("storage cannot be negative")


@dataclass(frozen=True)
class Storage:
    """What the quota allows now, and how much room is left."""

    state: State
    share_used: float
    remaining_bytes: int
    could_free_bytes: int
    may_accept: bool
    may_read: bool
    may_delete: bool
    reason: str = ""


def check_storage(quota: Quota) -> Storage:
    """Work out what `quota` still allows."""
    remaining = max(0, quota.limit_bytes - quota.used_bytes)
    share = min(1.0, quota.used_bytes / quota.limit_bytes)

    if quota.used_bytes >= quota.limit_bytes:
        state = State.FULL
    elif share >= NEARLY_FULL_AT:
        state = State.NEARLY_FULL
    else:
        state = State.FINE

    accepts = quota.used_bytes + quota.incoming_bytes <= quota.limit_bytes

    return Storage(
        state=state,
        share_used=share,
        remaining_bytes=remaining,
        could_free_bytes=quota.oldest_removable_bytes,
        may_accept=accepts,
        may_read=True,
        may_delete=True,
        reason=_reason(quota, state, accepts),
    )


def _reason(quota: Quota, state: State, accepts: bool) -> str:
    """The sentence explaining a storage state to the person."""
    suggestion = (
        " — clear older data to make room" if quota.oldest_removable_bytes > 0 else ""
    )

    if not accepts:
        over = quota.used_bytes + quota.incoming_bytes - quota.limit_bytes
        return f"this is {over // 1000} kB too large to store{suggestion}"

    if state is State.FULL:
        return f"storage is full{suggestion}"

    return ""
