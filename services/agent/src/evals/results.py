"""Benchmark results, append-only, keyed to the configuration that earned them."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Result:
    """One suite's score for one configuration."""

    fingerprint: str
    suite: str
    model: str
    score: float
    tasks: int
    variance: float
    approvals_per_run: float = 0.0

    def __post_init__(self) -> None:
        """Reject a result with no fingerprint or no tasks behind it."""
        if not self.fingerprint.strip():
            raise ValueError("a result must name the configuration that earned it")
        if self.tasks <= 0:
            raise ValueError("a score over no tasks is not a result")


@dataclass(frozen=True)
class Comparison:
    """The gap between two results, and whether it clears the noise."""

    difference: float
    significant: bool


class ResultsStore:
    """Recorded eval results, appended to a file."""

    def __init__(self, path: Path) -> None:
        """Bind the store to the file results are appended to."""
        self._path = path

    def record(self, result: Result) -> None:
        """Append `result` to the store."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a") as handle:
            handle.write(json.dumps(asdict(result)) + "\n")

    def all(self) -> list[Result]:
        """Every recorded result, oldest first."""
        if not self._path.exists():
            return []
        return [
            Result(**json.loads(line))
            for line in self._path.read_text().splitlines()
            if line.strip()
        ]

    def compare(self, before: str, after: str, *, suite: str) -> Comparison:
        """Compare the latest results of two configurations on `suite`."""
        first = self._latest(before, suite)
        second = self._latest(after, suite)
        difference = second.score - first.score

        noise = max(first.variance, second.variance)
        return Comparison(difference=difference, significant=abs(difference) > noise)

    def _latest(self, fingerprint: str, suite: str) -> Result:
        """The most recent result for this fingerprint and suite."""
        matches = [
            r for r in self.all() if r.fingerprint == fingerprint and r.suite == suite
        ]
        if not matches:
            raise LookupError(f"no result for {fingerprint} on {suite}")
        return matches[-1]
