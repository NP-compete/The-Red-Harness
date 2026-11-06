"""Which features an organisation may use."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Reason(Enum):
    """Why a feature is not available."""

    SUSPENDED = "suspended"
    UNKNOWN = "unknown"
    NOT_IN_PLAN = "not-in-plan"
    TURNED_OFF = "turned-off"
    TRIAL_ENDED = "trial-ended"


@dataclass(frozen=True)
class Entitlement:
    """The plan an org is on, what it turns on, and any trials."""

    plan: str
    plan_features: dict[str, tuple[str, ...]]
    enabled: tuple[str, ...]
    trials: dict[str, datetime]
    suspended: bool

    def __post_init__(self) -> None:
        """Reject an entitlement on a plan that does not exist."""
        if self.plan not in self.plan_features:
            raise ValueError(f"{self.plan} is not a plan")


@dataclass(frozen=True)
class Decision:
    """Whether a feature may be used, and how it could be got."""

    permitted: bool
    reason: Reason | None = None
    self_serve: bool = False
    on_trial: bool = False
    trial_ends: datetime | None = None


def may_use_feature(
    feature: str, entitlement: Entitlement, *, now: datetime
) -> Decision:
    """Decide whether `feature` may be used as of `now`."""
    if not feature.strip():
        raise ValueError("a feature must be named")

    if entitlement.suspended:
        return Decision(False, Reason.SUSPENDED)

    known = {name for names in entitlement.plan_features.values() for name in names}
    if feature not in known and feature not in entitlement.trials:
        return Decision(False, Reason.UNKNOWN)

    if feature in entitlement.plan_features[entitlement.plan]:
        if feature in entitlement.enabled:
            return Decision(True)
        return Decision(False, Reason.TURNED_OFF, self_serve=True)

    ends = entitlement.trials.get(feature)
    if ends is not None:
        if now < ends:
            return Decision(True, on_trial=True, trial_ends=ends)
        return Decision(False, Reason.TRIAL_ENDED)

    return Decision(False, Reason.NOT_IN_PLAN)
