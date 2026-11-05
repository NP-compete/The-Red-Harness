"""Authority for runs that nobody is watching."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch

from agent.src.security.resolver import AuthoritySource, Identity, ToolCall


@dataclass(frozen=True)
class Delegation:
    """One person's grant letting an agent act for them on named tools."""

    granter: str
    agent: str
    tools: list[str]
    servers: list[str]
    expires_at: datetime
    revoked: bool = False

    def covers(self, identity: Identity, call: ToolCall, now: datetime) -> bool:
        """Whether this grant covers `call` made by `identity` at `now`."""
        return (
            not self.revoked
            and now < self.expires_at
            and identity.subject == self.agent
            and identity.delegated_by == self.granter
            and any(fnmatch(call.name, pattern) for pattern in self.tools)
            and (not call.server or call.server in self.servers)
        )


class DelegatedAuthoritySource:
    """Authority that honours delegations before falling back to credentials."""

    def __init__(
        self,
        base: AuthoritySource,
        delegations: list[Delegation],
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        """Wrap `base`, honouring `delegations` as of `now`."""
        self._base = base
        self._delegations = delegations
        self._now = now

    async def aholds(self, identity: Identity, call: ToolCall) -> bool | None:
        """Whether `identity` holds authority for `call`, awaiting the base source."""
        granter = self._granter_for(identity, call)
        if not isinstance(granter, Identity):
            return granter
        ask = getattr(self._base, "aholds", self._base.holds)
        answer = ask(granter, call)
        return await answer if inspect.isawaitable(answer) else answer

    def _granter_for(self, identity: Identity, call: ToolCall) -> Identity | bool:
        """The identity to check against, or a settled answer if no grant covers the call."""
        if identity.delegated_by is None:
            return identity
        if not any(
            grant.covers(identity, call, self._now()) for grant in self._delegations
        ):
            return False
        return Identity(subject=identity.delegated_by)

    def holds(self, identity: Identity, call: ToolCall) -> bool | None:
        """Whether `identity` holds authority for `call`."""
        if identity.delegated_by is None:
            return self._base.holds(identity, call)

        now = self._now()
        if not any(grant.covers(identity, call, now) for grant in self._delegations):
            return False

        granter = Identity(subject=identity.delegated_by)
        return self._base.holds(granter, call)
