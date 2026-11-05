"""Opening something sealed by a key that has since been replaced."""

from __future__ import annotations

from typing import Callable, Iterable, TypeVar

Opened = TypeVar("Opened")


class NoKeyOpensIt(RuntimeError):
    """None of the keys offered could open the value."""


def open_with(
    keys: Iterable[str | None],
    sealed: str,
    open_it: Callable[[str, str], Opened],
) -> Opened:
    """Try each key in turn and return what the first one opens."""
    tried: list[str] = []
    for key in keys:
        if not key or not key.strip() or key in tried:
            continue
        tried.append(key)
        try:
            return open_it(key, sealed)
        except Exception:
            continue

    raise NoKeyOpensIt(
        f"none of the {len(tried)} key generation(s) available could open this "
        "value — it was sealed by a key this deployment no longer holds"
    )
