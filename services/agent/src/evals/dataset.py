"""Building a set of cases to test against, out of real runs."""

from __future__ import annotations

import random
from dataclasses import dataclass

MIN_USEFUL = 20


@dataclass(frozen=True)
class Candidate:
    """One case that might go into an eval dataset."""

    case_id: str
    question: str
    expected: str
    consented: bool
    contains_personal_data: bool
    labelled_by: str

    def __post_init__(self) -> None:
        """Reject a case that asks nothing."""
        if not self.question.strip():
            raise ValueError("a case must ask something")


@dataclass(frozen=True)
class Dataset:
    """The working and holdout splits, and what was excluded."""

    working: tuple[str, ...]
    holdout: tuple[str, ...]
    count: int
    excluded: dict[str, tuple[str, ...]]
    too_small: bool


def build_dataset(
    candidates: list[Candidate],
    *,
    holdout: float,
    seed: int = 0,
    strict: bool = False,
) -> Dataset:
    """Build a dataset from `candidates`, holding back a share."""
    if not 0 <= holdout < 1:
        raise ValueError("a holdout must leave something to work with")

    excluded: dict[str, list[str]] = {
        "no-consent": [],
        "personal-data": [],
        "unlabelled": [],
        "duplicate": [],
    }

    seen: set[str] = set()
    usable: list[str] = []

    for candidate in candidates:
        question = " ".join(candidate.question.lower().split())
        if not candidate.consented:
            excluded["no-consent"].append(candidate.case_id)
        elif candidate.contains_personal_data:
            excluded["personal-data"].append(candidate.case_id)
        elif not candidate.labelled_by.strip():
            excluded["unlabelled"].append(candidate.case_id)
        elif question in seen:
            excluded["duplicate"].append(candidate.case_id)
        else:
            seen.add(question)
            usable.append(candidate.case_id)

    if strict and not usable:
        raise ValueError("no cases survived; there is no dataset to build")

    held = _holdout(usable, holdout=holdout, seed=seed)

    return Dataset(
        working=tuple(case for case in usable if case not in held),
        holdout=tuple(sorted(held)),
        count=len(usable),
        excluded={reason: tuple(cases) for reason, cases in excluded.items()},
        too_small=len(usable) < MIN_USEFUL,
    )


def _holdout(usable: list[str], *, holdout: float, seed: int) -> set[str]:
    """The case ids held back, chosen deterministically from `seed`."""
    if holdout == 0 or not usable:
        return set()
    size = min(len(usable), max(1, round(len(usable) * holdout)))
    return set(random.Random(seed).sample(sorted(usable), size))
