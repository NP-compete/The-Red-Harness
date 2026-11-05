"""Comparing the access a connection asked for with what it was given."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reconciliation:
    """How the granted scopes compare to what was asked for."""

    ok: bool
    changed: bool
    narrowed: tuple[str, ...]
    widened: tuple[str, ...]
    message: str = ""


def reconcile(
    *, granted: list[str], requested: list[str], required: list[str] | None = None
) -> Reconciliation:
    """Compare `granted` against `requested`, checking nothing required is missing."""
    wanted = {scope.strip() for scope in requested if scope.strip()}
    if not wanted:
        raise ValueError("a connection must ask for something")

    have = {scope.strip() for scope in granted if scope.strip()}
    needed = {scope.strip() for scope in (required or []) if scope.strip()}

    narrowed = tuple(sorted(wanted - have))
    widened = tuple(sorted(have - wanted))

    missing_required = tuple(sorted(needed - have))

    return Reconciliation(
        ok=not missing_required,
        changed=bool(narrowed or widened),
        narrowed=narrowed,
        widened=widened,
        message=(
            f"this connection no longer allows {', '.join(missing_required)}"
            if missing_required
            else ""
        ),
    )
