"""How much failure is left before changes should stop."""

from __future__ import annotations

import pytest

from agent.src.security.error_budget import Budget, State, assess_budget


def budget(**kwargs) -> Budget:
    defaults = {"objective": 0.99, "total_runs": 10_000, "failed_runs": 50}
    defaults.update(kwargs)
    return Budget(**defaults)


def test_a_healthy_service_has_budget_left():
    assert assess_budget(budget()).state is State.HEALTHY


def test_the_share_of_budget_used_is_reported():
    assert assess_budget(budget()).used == pytest.approx(0.5)


def test_the_number_of_failures_still_allowed_is_reported():
    assert assess_budget(budget()).failures_left == 50


def test_a_service_near_its_limit_is_at_risk():
    assert assess_budget(budget(failed_runs=85)).state is State.AT_RISK


def test_a_service_over_its_limit_has_spent_the_budget():
    assert assess_budget(budget(failed_runs=120)).state is State.EXHAUSTED


def test_an_exhausted_budget_has_no_failures_left():
    assert assess_budget(budget(failed_runs=120)).failures_left == 0


def test_an_exhausted_budget_never_reports_more_than_fully_used():
    assert assess_budget(budget(failed_runs=120)).used == 1.0


def test_risky_changes_are_allowed_while_healthy():
    assert assess_budget(budget()).may_deploy is True


def test_risky_changes_are_allowed_but_flagged_when_at_risk():
    result = assess_budget(budget(failed_runs=85))
    assert result.may_deploy is True and result.warn is True


def test_risky_changes_stop_once_the_budget_is_spent():
    assert assess_budget(budget(failed_runs=120)).may_deploy is False


def test_a_freeze_says_why():
    assert "budget" in assess_budget(budget(failed_runs=120)).reason


def test_an_urgent_fix_is_allowed_through_a_freeze():
    assert assess_budget(budget(failed_runs=120), is_fix=True).may_deploy is True


def test_an_urgent_fix_through_a_freeze_is_still_recorded_as_exceptional():
    assert assess_budget(budget(failed_runs=120), is_fix=True).exceptional is True


def test_an_ordinary_change_while_healthy_is_not_exceptional():
    assert assess_budget(budget()).exceptional is False


def test_a_service_with_no_runs_yet_is_not_judged():
    assert assess_budget(budget(total_runs=0, failed_runs=0)).state is State.UNKNOWN


def test_a_service_with_no_runs_may_still_be_changed():
    assert assess_budget(budget(total_runs=0, failed_runs=0)).may_deploy is True


def test_more_failures_than_runs_is_refused():
    with pytest.raises(ValueError):
        Budget(objective=0.99, total_runs=10, failed_runs=11)


@pytest.mark.parametrize("objective", [0.0, 1.0, 1.5])
def test_an_impossible_objective_is_refused(objective):
    with pytest.raises(ValueError):
        Budget(objective=objective, total_runs=10, failed_runs=0)
