"""Measuring whether retrieval finds the right documents (E35-T4)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import pvariance

DEFAULT_K = 8


@dataclass(frozen=True)
class Case:
    """One query, and the documents that should come back for it."""

    query: str
    relevant: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a case with no query, or one naming no relevant document."""
        if not self.query.strip():
            raise ValueError("a retrieval case needs a query")
        if not self.relevant:
            raise ValueError(
                f"the case {self.query!r} names no relevant document, so it can "
                "neither pass nor fail — give it one or drop it"
            )


@dataclass(frozen=True)
class CaseScore:
    """One retrieval case's recall and precision, and what it missed."""

    query: str
    recall: float
    precision: float
    missed: tuple[str, ...]


@dataclass(frozen=True)
class Measurement:
    """Recall and precision over a corpus at a given k."""

    corpus: str
    k: int
    recall: float
    precision: float
    cases: tuple[CaseScore, ...]

    @property
    def variance(self) -> float:
        """How much the cases disagree with each other."""
        if not self.cases:
            return 0.0
        return pvariance([c.recall for c in self.cases])

    @property
    def worst(self) -> tuple[CaseScore, ...]:
        """The cases that found least, so a reader starts there."""
        return tuple(sorted(self.cases, key=lambda c: c.recall))


def measure(
    cases: Sequence[Case],
    *,
    search: Callable[[str, int], Sequence[str]],
    corpus: str,
    k: int = DEFAULT_K,
) -> Measurement:
    """Run every case through `search` and score what came back."""
    if not cases:
        raise ValueError("a measurement over no cases is not a measurement")
    if k < 1:
        raise ValueError("a retrieval scored over no documents is not scored")

    scores: list[CaseScore] = []
    for case in cases:
        found = list(search(case.query, k))[:k]
        hits = [one for one in case.relevant if one in found]
        scores.append(
            CaseScore(
                query=case.query,
                recall=len(hits) / len(case.relevant),
                precision=(len(hits) / len(found)) if found else 0.0,
                missed=tuple(one for one in case.relevant if one not in found),
            )
        )

    return Measurement(
        corpus=corpus,
        k=k,
        recall=sum(s.recall for s in scores) / len(scores),
        precision=sum(s.precision for s in scores) / len(scores),
        cases=tuple(scores),
    )


def as_result(measurement: Measurement, *, fingerprint: str, model: str = "") -> object:
    """The measurement as a benchmark result, so the gate can use it."""
    from agent.src.evals.results import Result

    return Result(
        fingerprint=fingerprint,
        suite=f"retrieval:{measurement.corpus}",
        model=model,
        score=measurement.recall,
        tasks=len(measurement.cases),
        variance=measurement.variance,
    )


def read_cases(raw: object) -> list[Case]:
    """Cases from a declared dataset, refusing anything unusable."""
    if not isinstance(raw, list):
        raise ValueError("a retrieval dataset is a list of cases")

    found: list[Case] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"case {index} is not a mapping")
        relevant = entry.get("relevant") or entry.get("expect") or []
        if isinstance(relevant, str):
            relevant = [relevant]
        found.append(
            Case(
                query=str(entry.get("query") or ""),
                relevant=tuple(str(one) for one in relevant),
            )
        )
    return found
