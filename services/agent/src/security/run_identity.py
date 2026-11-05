"""Who a run is acting as."""

from __future__ import annotations

from agent.src.security.resolver import Identity


def identify(
    *,
    claims: dict | None,
    agent: str | None = None,
    granted_by: str | None = None,
) -> Identity | None:
    """The identity a run acts as, from its claims or its delegation."""
    subject = (claims or {}).get("sub", "").strip()
    if subject:
        return Identity(subject=subject, groups=tuple((claims or {}).get("groups", ())))

    if agent and granted_by:
        return Identity(subject=agent, delegated_by=granted_by)

    return None
