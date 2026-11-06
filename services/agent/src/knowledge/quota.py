"""How much one person may keep in the library."""

from __future__ import annotations

from typing import Any

from agent.src.knowledge.scopes import Scope


class QuotaExceeded(ValueError):
    """Storing this would put the owner over their limit."""


def stored_bytes(store: Any, *, owner: str) -> int:
    """What this person is keeping, in bytes."""
    return sum(
        len(document.text.encode("utf-8"))
        for document in store.documents_in(scope=Scope.USER, owner=owner)
    )


def check_room_for(size: int, *, store: Any, owner: str, limit: int) -> None:
    """Raise unless this many more bytes would still fit."""
    if size <= 0:
        raise ValueError("an empty document is never worth storing")

    used = stored_bytes(store, owner=owner)
    if used + size > limit:
        raise QuotaExceeded(
            f"storing {size} more bytes would put you over your limit: "
            f"{used} of {limit} bytes used"
        )
