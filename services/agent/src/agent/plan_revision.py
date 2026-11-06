"""Amending a plan when a step turns out not to be possible."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    """One step of a plan, and whether it has already had effects."""

    name: str
    done: bool
    had_effects: bool
    required: bool


@dataclass(frozen=True)
class Revision:
    """A plan after revision, and whether it does less than before."""

    steps: list[Step]
    narrowed: bool

    @property
    def worth_mentioning(self) -> bool:
        """Whether the revision is worth telling the person about."""
        return True

    @property
    def needs_agreement(self) -> bool:
        """Whether the revision narrows the plan enough to need agreement."""
        return self.narrowed


def revise(plan: list[Step], *, blocked: str, instead: list[Step]) -> Revision:
    """Replace the blocked step of `plan` with `instead`."""
    if not plan:
        raise ValueError("there is no plan to revise")

    at = next((i for i, step in enumerate(plan) if step.name == blocked), None)
    if at is None:
        raise ValueError(f"{blocked} is not in the plan")
    if plan[at].done:
        raise ValueError(f"{blocked} has already been done")

    if any(step.done for step in instead):
        raise ValueError("a replacement step cannot already be done")

    taken = {step.name for step in plan} - {blocked}
    clashing = taken & {step.name for step in instead}
    if clashing:
        raise ValueError(f"the plan already has {', '.join(sorted(clashing))}")

    steps = plan[:at] + instead + plan[at + 1 :]

    return Revision(
        steps=steps,
        narrowed=not instead and plan[at].required,
    )
