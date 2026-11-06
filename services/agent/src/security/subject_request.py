"""Working out what can be done about the data held on a person."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

DEADLINE = timedelta(days=30)


class Kind(Enum):
    """Whether a subject is asking for their data or its deletion."""

    EXPORT = "export"
    DELETE = "delete"


@dataclass(frozen=True)
class Store:
    """One store that may hold a person's data."""

    name: str
    holds_data: bool
    on_legal_hold: bool
    deletable: bool

    def __post_init__(self) -> None:
        """Reject a store with no name."""
        if not self.name.strip():
            raise ValueError("a store must have a name")


@dataclass(frozen=True)
class Plan:
    """What a subject request will cover, what it cannot, and when it is due."""

    kind: Kind
    included: tuple[str, ...]
    withheld: dict[str, str]
    complete: bool
    due_at: datetime
    notice: str = ""


def plan_request(kind: Kind, *, stores: tuple[Store, ...], now: datetime) -> Plan:
    """Plan a subject request of `kind` across `stores`."""
    if not stores:
        raise ValueError("there are no stores to look in")

    holding = sorted(
        (store for store in stores if store.holds_data), key=lambda store: store.name
    )

    included: list[str] = []
    withheld: dict[str, str] = {}

    for store in holding:
        if kind is Kind.EXPORT:
            included.append(store.name)
            continue
        if store.on_legal_hold:
            withheld[store.name] = "under legal hold"
        elif not store.deletable:
            withheld[store.name] = "kept as a record"
        else:
            included.append(store.name)

    return Plan(
        kind=kind,
        included=tuple(included),
        withheld=withheld,
        complete=not withheld,
        due_at=now + DEADLINE,
        notice=(f"data remains in {', '.join(sorted(withheld))}" if withheld else ""),
    )
