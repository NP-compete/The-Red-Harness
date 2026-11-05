"""Choosing where a run may be processed, and where its traffic may pass."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Refusal(Enum):
    """Why a run could not be placed."""

    NO_ALLOWED_REGION = "no-allowed-region"


@dataclass(frozen=True)
class Policy:
    """Where runs may be placed, where they should be, and what they may cross."""

    allowed_regions: tuple[str, ...]
    preferred_region: str
    allow_transit_through: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a policy allowing nowhere, or preferring a disallowed region."""
        if not self.allowed_regions:
            raise ValueError("a policy must allow somewhere to run")
        if self.preferred_region not in self.allowed_regions:
            raise ValueError("the preferred region must be one of the allowed regions")


@dataclass(frozen=True)
class Placement:
    """Where a run was placed, and whether that is a degraded choice."""

    region: str
    degraded: bool
    refusal: Refusal | None = None
    reason: str = ""
    _transit: frozenset[str] = field(default_factory=frozenset)

    def may_transit(self, region: str) -> bool:
        """Whether data may pass through `region`."""
        return region in self._transit


def place_run(policy: Policy, *, available: tuple[str, ...]) -> Placement:
    """Place a run in the best available region the policy allows."""
    candidates = [region for region in policy.allowed_regions if region in available]

    if not candidates:
        return Placement(
            region="",
            degraded=False,
            refusal=Refusal.NO_ALLOWED_REGION,
            reason=(
                "none of the available regions are allowed; "
                f"allowed: {', '.join(policy.allowed_regions)}"
            ),
        )

    region = (
        policy.preferred_region
        if policy.preferred_region in candidates
        else candidates[0]
    )

    return Placement(
        region=region,
        degraded=region != policy.preferred_region,
        _transit=frozenset(policy.allowed_regions)
        | frozenset(policy.allow_transit_through),
    )
