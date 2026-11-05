"""How well the corpus answers questions it is supposed to."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence


@dataclass(frozen=True)
class Case:
    """A question, and the documents that should answer it."""

    query: str
    relevant: set[str]


@dataclass(frozen=True)
class Quality:
    """Recall and precision over a number of cases."""

    recall: float
    precision: float
    cases: int


def recall_at(found: Sequence[str], relevant: set[str], *, k: int) -> float | None:
    """Of the documents that should have come back, how many did."""
    if not relevant:
        return None
    seen = set(found[:k])
    return len(seen & relevant) / len(relevant)


def precision_at(found: Sequence[str], relevant: set[str], *, k: int) -> float | None:
    """Of what came back, how much should have."""
    kept = list(found[:k])
    if not kept:
        return None
    return len([one for one in kept if one in relevant]) / len(kept)


def measure(
    search: Callable[[str], Sequence[str]],
    cases: Iterable[Case],
    *,
    k: int = 5,
) -> Quality:
    """Run every case and average both numbers."""
    cases = list(cases)
    if not cases:
        raise ValueError("there are no cases to measure")
    if any(not case.relevant for case in cases):
        raise ValueError("a case with no relevant documents cannot be scored")

    recalls: list[float] = []
    precisions: list[float] = []
    for case in cases:
        found = list(search(case.query))
        got_recall = recall_at(found, case.relevant, k=k)
        if got_recall is not None:
            recalls.append(got_recall)
        got_precision = precision_at(found, case.relevant, k=k)
        if got_precision is not None:
            precisions.append(got_precision)

    return Quality(
        recall=sum(recalls) / len(recalls) if recalls else 0.0,
        precision=sum(precisions) / len(precisions) if precisions else 0.0,
        cases=len(cases),
    )
