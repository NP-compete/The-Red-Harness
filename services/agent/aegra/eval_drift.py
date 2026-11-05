"""Turning stored eval runs into a reading of which way scores are going."""

from __future__ import annotations

from typing import Any, Sequence

from agent.src.evals.drift import Run, detect_drift


def rows_to_runs(rows: Sequence[Sequence[Any]]) -> list[Run]:
    """Rows of `(id, score, pass, fail, error)`, oldest first."""
    runs = []
    for run_id, score, passed, failed, errored in rows:
        if score is None:
            continue
        runs.append(
            Run(
                run=str(run_id),
                score=float(score),
                cases=int(passed or 0) + int(failed or 0) + int(errored or 0),
            )
        )
    runs.reverse()
    return runs


def summarise_drift(
    rows: Sequence[Sequence[Any]], *, baseline: float
) -> dict[str, Any]:
    """Eval drift against `baseline`, as a response body."""
    drift = detect_drift(rows_to_runs(rows), baseline=baseline)

    return {
        "movement": drift.movement.value,
        "gap": drift.gap,
        "outliers": drift.outliers,
        "needs_attention": drift.needs_attention,
    }
