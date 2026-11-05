"""Planning an action over many items, and reporting honestly afterwards."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

CONFIRM_ABOVE = 20
MAX_ITEMS = 1000
DESTRUCTIVE = {"delete", "purge", "revoke"}


class Outcome(Enum):
    """What happened to one item of a bulk action."""

    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class Plan:
    """What a bulk action would touch, and whether to confirm first."""

    items: tuple[str, ...]
    count: int
    runnable: bool
    needs_confirmation: bool
    confirmation: str = ""
    reason: str = ""


@dataclass(frozen=True)
class Summary:
    """How a bulk action went, and what to tell the person."""

    done: int
    skipped: int
    failed: int
    failed_items: tuple[str, ...]
    all_succeeded: bool
    message: str


def plan_bulk(items: list[str], *, action: str) -> Plan:
    """Plan `action` over `items`, deduplicated."""
    if not action.strip():
        raise ValueError("a bulk action must have a name")

    unique = tuple(dict.fromkeys(items))

    if not unique:
        return Plan(
            (),
            0,
            runnable=False,
            needs_confirmation=False,
            reason="there is nothing selected",
        )

    if len(unique) > MAX_ITEMS:
        return Plan(
            unique,
            len(unique),
            runnable=False,
            needs_confirmation=False,
            reason=f"at most {MAX_ITEMS} items can be changed at once",
        )

    needs = len(unique) > CONFIRM_ABOVE or action in DESTRUCTIVE

    return Plan(
        items=unique,
        count=len(unique),
        runnable=True,
        needs_confirmation=needs,
        confirmation=f"{action} {len(unique)} items?" if needs else "",
    )


def summarise_bulk(results: dict[str, Outcome]) -> Summary:
    """Summarise the outcome of a bulk action."""
    if not results:
        raise ValueError("there is nothing to summarise")

    counts = {outcome: 0 for outcome in Outcome}
    for outcome in results.values():
        counts[outcome] += 1

    failed_items = tuple(
        item for item, outcome in results.items() if outcome is Outcome.FAILED
    )

    parts = [f"{counts[Outcome.DONE]} done"]
    if counts[Outcome.SKIPPED]:
        parts.append(f"{counts[Outcome.SKIPPED]} skipped")
    if counts[Outcome.FAILED]:
        parts.append(f"{counts[Outcome.FAILED]} failed")

    return Summary(
        done=counts[Outcome.DONE],
        skipped=counts[Outcome.SKIPPED],
        failed=counts[Outcome.FAILED],
        failed_items=failed_items,
        all_succeeded=counts[Outcome.FAILED] == 0,
        message=", ".join(parts),
    )
