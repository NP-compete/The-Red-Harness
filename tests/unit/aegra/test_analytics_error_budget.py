"""Reading the error budget off what the runs actually did."""

from __future__ import annotations

import pytest

from agent.aegra.analytics_error_budget import budget_from_counts


def test_a_quiet_window_of_successes_is_healthy():
    assert budget_from_counts(runs=1000, errors=2, objective=0.99)["state"] == "healthy"


def test_a_window_eating_its_budget_is_at_risk():
    assert budget_from_counts(runs=1000, errors=9, objective=0.99)["state"] == "at-risk"


def test_a_window_past_its_budget_is_exhausted():
    assert (
        budget_from_counts(runs=1000, errors=20, objective=0.99)["state"] == "exhausted"
    )


def test_how_much_of_the_budget_is_gone_is_reported():
    assert budget_from_counts(runs=1000, errors=5, objective=0.99)[
        "used"
    ] == pytest.approx(0.5)


def test_how_many_failures_are_left_is_reported():
    assert budget_from_counts(runs=1000, errors=5, objective=0.99)["failures_left"] == 5


def test_a_window_with_no_runs_says_it_cannot_tell():
    assert budget_from_counts(runs=0, errors=0, objective=0.99)["state"] == "unknown"


def test_an_exhausted_budget_holds_back_a_deploy():
    assert (
        budget_from_counts(runs=1000, errors=20, objective=0.99)["may_deploy"] is False
    )


def test_a_healthy_budget_lets_a_deploy_through():
    assert budget_from_counts(runs=1000, errors=2, objective=0.99)["may_deploy"] is True


def test_an_exhausted_budget_says_why():
    assert budget_from_counts(runs=1000, errors=20, objective=0.99)["reason"]


def test_more_errors_than_runs_is_refused():
    with pytest.raises(ValueError):
        budget_from_counts(runs=10, errors=11, objective=0.99)


def test_an_objective_leaving_no_room_for_failure_is_refused():
    with pytest.raises(ValueError):
        budget_from_counts(runs=10, errors=1, objective=1.0)
