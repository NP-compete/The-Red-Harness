"""Which networks the platform may be reached from."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from enum import Enum


class Outcome(Enum):
    """How a source address compared to the allowlist."""

    ALLOWED = "allowed"
    NOT_ALLOWED = "not-allowed"
    BREAK_GLASS = "break-glass"
    UNREADABLE = "unreadable"


@dataclass(frozen=True)
class Allowlist:
    """The network ranges allowed, and who may break the glass."""

    ranges: tuple[str, ...]
    enforced: bool
    break_glass_roles: tuple[str, ...]
    _networks: tuple = field(default=(), repr=False, compare=False)

    def __post_init__(self) -> None:
        """Parse the ranges, rejecting any that is not a network."""
        networks = []
        for text in self.ranges:
            try:
                network = ipaddress.ip_network(text, strict=False)
            except ValueError as error:
                raise ValueError(f"{text} is not a network range") from error
            if network.prefixlen == 0:
                raise ValueError(f"{text} allows everything, which is not an allowlist")
            networks.append(network)
        object.__setattr__(self, "_networks", tuple(networks))

    def contains(self, address: ipaddress._BaseAddress) -> bool:
        """Whether `address` falls in any allowed range."""
        return any(address in network for network in self._networks)


@dataclass(frozen=True)
class Check:
    """Whether a source is permitted, and under what exception."""

    outcome: Outcome
    permitted: bool
    would_refuse: bool = False
    exceptional: bool = False
    reason: str = ""


def check_source(source: str, allowlist: Allowlist, *, roles: tuple[str, ...]) -> Check:
    """Judge `source` against the allowlist, honouring break-glass roles."""
    try:
        address = ipaddress.ip_address(source)
    except ValueError:
        return Check(
            Outcome.UNREADABLE,
            permitted=False,
            reason="the source address is unreadable",
        )

    inside = allowlist.contains(address)

    if inside:
        return Check(Outcome.ALLOWED, permitted=True)

    if not allowlist.enforced:
        return Check(Outcome.ALLOWED, permitted=True, would_refuse=True)

    if set(roles) & set(allowlist.break_glass_roles):
        return Check(
            Outcome.BREAK_GLASS,
            permitted=True,
            exceptional=True,
            reason="allowed from outside the permitted networks",
        )

    return Check(
        Outcome.NOT_ALLOWED,
        permitted=False,
        reason="this network is not permitted to reach the platform",
    )
