"""Everything that has to be true before a suite is worth starting (E1-T5)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _harness2() -> Path:
    """Where the benchmark datasets live, if they live anywhere.

    A sibling checkout outside this repository. `REPO_ROOT.parents[1]`
    assumed the repo sat two directories inside a wider workspace —
    true on the machine this was written on, an `IndexError` at `/src`
    in a container, and a path to nothing in a fresh clone. Overridable
    so the location is a setting rather than a guess about the layout
    above us.
    """
    import os

    if named := os.environ.get("HARNESS2_DIR"):
        return Path(named)
    above = REPO_ROOT.parents
    base = above[1] if len(above) > 1 else REPO_ROOT
    return base / "examples" / "harness2"


HARNESS2 = _harness2()

DATASETS = {
    "jb": HARNESS2 / "dependencies" / "job-bench-eval" / "dataset" / "main",
    "wbb": HARNESS2 / "dependencies" / "workbuddy-bench" / "datasets",
    "lab": HARNESS2 / "dependencies" / "harvey-labs",
}

MOCKS = ("mock", "mock-model", "stub")


@dataclass(frozen=True)
class Check:
    """One preflight check and what it found."""

    name: str
    ok: bool
    detail: str

    def __str__(self) -> str:
        """The check rendered as one line."""
        return f"{'ok  ' if self.ok else 'MISS'}  {self.name}: {self.detail}"


def dataset_check(suite: str) -> Check:
    """Check that the suite's dataset is present."""
    where = DATASETS.get(suite)
    if where is None:
        return Check(
            "dataset", False, f"no suite called {suite!r}; try {sorted(DATASETS)}"
        )
    if where.is_dir() and any(where.iterdir()):
        return Check("dataset", True, str(where))
    return Check(
        "dataset",
        False,
        f"{where} is empty or absent. The suites are vendored as pointers — "
        f"see {HARNESS2 / 'dependencies' / 'PINNED.md'} for the revisions to fetch.",
    )


def judge_check(model: str) -> Check:
    """Check that a judge model is configured."""
    name = (model or "").strip()
    if not name:
        return Check(
            "judge model",
            False,
            "no model configured. The suite scores with a rubric judge, which "
            "is a model call; without one a run produces attempts and no score.",
        )
    if any(mock in name.lower() for mock in MOCKS):
        return Check(
            "judge model",
            False,
            f"{name!r} is a mock. It answers every prompt with the prompt, so a "
            "judge reading it scores the echo — a number that means nothing is "
            "worse than no number.",
        )
    return Check("judge model", True, name)


def agent_check(url: str, effects: str) -> Check:
    """Check that the agent is safe to benchmark against."""
    from scripts.bench.guard import BenchRefused, check_safe_to_run

    try:
        check_safe_to_run(effects=effects)
    except BenchRefused as refused:
        return Check("agent", False, str(refused))
    return Check("agent", True, f"{url} is dry_run")


def driver_check() -> Check:
    """Whether anything here can turn a dataset into scores."""
    return Check(
        "suite driver",
        False,
        "not wired up. scripts/bench/executor.py runs one task against this "
        "agent and is what harness2's runner calls; the runner itself, with "
        "its substrates and rubric judge, is not vendored here.",
    )


def preflight(*, suite: str, url: str, effects: str, model: str) -> list[Check]:
    """Every prerequisite, in the order somebody would fix them."""
    return [
        agent_check(url, effects),
        dataset_check(suite),
        judge_check(model),
        driver_check(),
    ]
