"""Reading the error budget off what the runs actually did."""

from __future__ import annotations

from typing import Any

from agent.src.security.error_budget import Budget, assess_budget


def budget_from_counts(*, runs: int, errors: int, objective: float) -> dict[str, Any]:
    """The error budget as a response body, from run and error counts."""
    assessed = assess_budget(
        Budget(objective=objective, total_runs=runs, failed_runs=errors)
    )

    return {
        "state": assessed.state.value,
        "used": assessed.used,
        "failures_left": assessed.failures_left,
        "may_deploy": assessed.may_deploy,
        "warn": assessed.warn,
        "exceptional": assessed.exceptional,
        "reason": assessed.reason,
        "objective": objective,
    }
