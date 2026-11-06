"""Where a score is kept, and what it is a score of."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    """The current UTC time, to the second."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Row:
    """One recorded benchmark run."""

    fingerprint: str
    suite: str
    model: str
    score: float
    tasks: int = 0
    errors: int = 0
    at: str = field(default_factory=_now)


@dataclass(frozen=True)
class Delta:
    """One suite's score before and after."""

    suite: str
    before: float
    after: float

    @property
    def delta(self) -> float:
        """How much the score moved."""
        return self.after - self.before


def record(row: Row, *, path: Path) -> None:
    """Add one run. Never rewrites what is already there."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as out:
        out.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def read_rows(path: Path) -> list[Row]:
    """Every recorded run in `path`, or nothing if it is not there."""
    if not path.is_file():
        return []

    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(Row(**json.loads(line)))
        except (json.JSONDecodeError, TypeError):
            continue
    return rows


def _latest(rows: list[Row], fingerprint: str) -> dict[str, Row]:
    """The current score per suite for one configuration."""
    found: dict[str, Row] = {}
    for row in rows:
        if row.fingerprint != fingerprint:
            continue
        seen = found.get(row.suite)
        if seen is None or row.at >= seen.at:
            found[row.suite] = row
    return found


def compare(rows: list[Row], before: str, after: str) -> list[Delta]:
    """Per-suite deltas between two configurations."""
    left, right = _latest(rows, before), _latest(rows, after)
    for name, found in ((before, left), (after, right)):
        if not found:
            raise ValueError(f"no runs recorded for {name}")

    models = {row.model for row in list(left.values()) + list(right.values())}
    if len(models) > 1:
        raise ValueError(
            f"these runs used more than one model ({', '.join(sorted(models))}); "
            "a delta across models says nothing about the configurations"
        )

    return [
        Delta(suite=suite, before=left[suite].score, after=right[suite].score)
        for suite in sorted(set(left) & set(right))
    ]


def unmatched(rows: list[Row], before: str, after: str) -> list[str]:
    """Suites only one side ran."""
    left, right = _latest(rows, before), _latest(rows, after)
    return sorted(set(left) ^ set(right))
