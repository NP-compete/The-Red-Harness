"""Choosing which stored credential a tool call may use, if any."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Refusal(Enum):
    """Why no credential could be chosen."""

    NO_BINDING = "no-binding"
    NO_CREDENTIAL = "no-credential"
    SCOPE_MISSING = "scope-missing"
    NOT_YOURS = "not-yours"


@dataclass(frozen=True)
class Credential:
    """One stored credential, its scopes and who owns it."""

    name: str
    scopes: tuple[str, ...]
    owner: str
    shared: bool


@dataclass(frozen=True)
class Binding:
    """Which credential a tool uses, and the scope it needs."""

    tool: str
    credential: str
    required_scope: str

    def __post_init__(self) -> None:
        """Reject a binding that does not say which scope is needed."""
        if not self.required_scope.strip():
            raise ValueError("a binding must say which scope the tool needs")


@dataclass(frozen=True)
class Choice:
    """The credential chosen for a call, or the refusal that stopped it."""

    credential: str = ""
    scope: str = ""
    refusal: Refusal | None = None
    reason: str = ""


def credential_for(
    tool: str,
    *,
    caller: str,
    bindings: tuple[Binding, ...],
    credentials: tuple[Credential, ...],
) -> Choice:
    """Choose the credential `caller` should use for `tool`."""
    if not caller.strip():
        raise ValueError("a credential is always used by someone")

    matching = [binding for binding in bindings if binding.tool == tool]
    if len(matching) > 1:
        raise ValueError(f"{tool} is bound to more than one credential")
    if not matching:
        return Choice(
            refusal=Refusal.NO_BINDING, reason=f"{tool} has no credential bound to it"
        )

    binding = matching[0]
    found = next((c for c in credentials if c.name == binding.credential), None)
    if found is None:
        return Choice(
            refusal=Refusal.NO_CREDENTIAL,
            reason=f"{binding.credential} is not stored",
        )

    if not found.shared and found.owner != caller:
        return Choice(
            refusal=Refusal.NOT_YOURS,
            reason=f"{binding.credential} is not yours to use",
        )

    if binding.required_scope not in found.scopes:
        return Choice(
            refusal=Refusal.SCOPE_MISSING,
            reason=f"{binding.credential} does not grant {binding.required_scope}",
        )

    return Choice(credential=found.name, scope=binding.required_scope)
