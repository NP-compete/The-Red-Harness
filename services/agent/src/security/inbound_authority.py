"""Whose authority an inbound run carries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SERVICE_PREFIX = "service:"

_SCOPES = ("read", "act")


class AuthorityRefused(PermissionError):
    """The run has no authority it could legitimately carry."""


@dataclass(frozen=True)
class Authority:
    """Who an inbound run acts as, and whether it may use connections."""

    user_id: str
    audit_as: str
    may_use_connections: bool

    def as_metadata(self) -> dict[str, Any]:
        """What the run is told about who it is for."""
        return {
            "user_id": self.user_id,
            "inbound": True,
            "inbound_caller": self.audit_as,
            "may_use_connections": self.may_use_connections,
        }


def authority_for(*, mode: str, caller: str, scope: str) -> Authority:
    """What an inbound run may be, or a refusal."""
    if scope not in _SCOPES:
        raise AuthorityRefused(f"{scope!r} is not a scope this agent publishes")

    if not caller:
        raise AuthorityRefused("An inbound run needs a caller to belong to")

    if mode == "oauth":
        return Authority(
            user_id=caller,
            audit_as=caller,
            may_use_connections=scope == "act",
        )

    if mode == "service_token":
        return Authority(
            user_id=f"{SERVICE_PREFIX}{caller}",
            audit_as=caller,
            may_use_connections=False,
        )

    raise AuthorityRefused(
        f"{mode!r} is not a mode an inbound run can carry. "
        "A run is the caller's or a service identity's; it is never the agent's."
    )
