"""Choosing which runs a person should look at."""

from __future__ import annotations

import random
from dataclasses import dataclass

SHARES = {"disliked": 0.3, "failed": 0.3, "ordinary": 0.4}


@dataclass(frozen=True)
class Run:
    """One run that could be sampled for review."""

    run_id: str
    outcome: str
    reviewed: bool
    rated_down: bool


def choose_sample(population: list[Run], *, size: int, seed: int) -> list[Run]:
    """Choose `size` unreviewed runs, deterministically from `seed`."""
    if size < 0:
        raise ValueError("a sample cannot be of negative size")

    unseen = [run for run in population if not run.reviewed]
    if not unseen or size == 0:
        return []

    strata: dict[str, list[Run]] = {name: [] for name in SHARES}
    for run in unseen:
        if run.rated_down:
            strata["disliked"].append(run)
        elif run.outcome != "ok":
            strata["failed"].append(run)
        else:
            strata["ordinary"].append(run)

    chooser = random.Random(seed)
    chosen: list[Run] = []

    for name, share in SHARES.items():
        available = sorted(strata[name], key=lambda run: run.run_id)
        if not available:
            continue
        want = min(len(available), max(1, round(size * share)))
        chosen.extend(chooser.sample(available, want))

    if len(chosen) > size:
        chosen = chooser.sample(chosen, size)
    elif len(chosen) < size:
        picked = {run.run_id for run in chosen}
        rest = sorted(
            (run for run in unseen if run.run_id not in picked), key=lambda r: r.run_id
        )
        chosen.extend(chooser.sample(rest, min(len(rest), size - len(chosen))))

    return sorted(chosen, key=lambda run: run.run_id)
