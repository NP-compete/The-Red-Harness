"""Deciding whether a change may be released."""

from __future__ import annotations

import pytest

from agent.src.evals.release_gate import Blocker, Signals, decide_release


def signals(**kwargs) -> Signals:
    defaults = {
        "suite_may_gate": True,
        "judge_may_gate": True,
        "regressed": False,
        "broken_cases": (),
        "error_budget_spent": False,
        "is_fix": False,
        "dataset_usable": True,
    }
    defaults.update(kwargs)
    return Signals(**defaults)


def test_everything_in_order_releases():
    assert decide_release(signals()).release is True


def test_a_clean_decision_has_no_blockers():
    assert decide_release(signals()).blockers == ()


def test_a_regression_blocks_the_release():
    assert (
        Blocker.REGRESSED
        in decide_release(signals(regressed=True, broken_cases=("a",))).blockers
    )


def test_a_regression_names_what_broke():
    decision = decide_release(signals(regressed=True, broken_cases=("a", "b")))
    assert "a, b" in decision.reason


def test_a_wobbly_suite_blocks_the_release():
    assert (
        Blocker.UNRELIABLE_SUITE
        in decide_release(signals(suite_may_gate=False)).blockers
    )


def test_an_unproven_judge_blocks_the_release():
    assert (
        Blocker.UNPROVEN_JUDGE in decide_release(signals(judge_may_gate=False)).blockers
    )


def test_a_dataset_that_cannot_be_trusted_blocks_the_release():
    assert (
        Blocker.WEAK_DATASET in decide_release(signals(dataset_usable=False)).blockers
    )


def test_a_spent_error_budget_blocks_the_release():
    assert (
        Blocker.BUDGET_SPENT
        in decide_release(signals(error_budget_spent=True)).blockers
    )


def test_an_urgent_fix_passes_a_spent_budget():
    decision = decide_release(signals(error_budget_spent=True, is_fix=True))
    assert decision.release is True


def test_an_urgent_fix_is_recorded_as_exceptional():
    decision = decide_release(signals(error_budget_spent=True, is_fix=True))
    assert decision.exceptional is True


def test_an_urgent_fix_does_not_excuse_a_regression():
    decision = decide_release(signals(regressed=True, broken_cases=("a",), is_fix=True))
    assert decision.release is False


def test_an_urgent_fix_does_not_excuse_an_unreliable_suite():
    assert decide_release(signals(suite_may_gate=False, is_fix=True)).release is False


def test_several_blockers_are_all_reported():
    decision = decide_release(signals(suite_may_gate=False, judge_may_gate=False))
    assert set(decision.blockers) == {Blocker.UNRELIABLE_SUITE, Blocker.UNPROVEN_JUDGE}


def test_the_most_serious_blocker_is_named_first():
    decision = decide_release(
        signals(regressed=True, broken_cases=("a",), judge_may_gate=False)
    )
    assert decision.blockers[0] is Blocker.REGRESSED


def test_a_clean_release_is_not_exceptional():
    assert decide_release(signals()).exceptional is False


def test_a_blocked_release_says_what_would_unblock_it():
    decision = decide_release(signals(suite_may_gate=False))
    assert "suite" in decision.next_step


def test_a_clean_release_needs_no_next_step():
    assert decide_release(signals()).next_step == ""


def test_a_regression_without_named_cases_is_refused():
    with pytest.raises(ValueError):
        Signals(
            suite_may_gate=True,
            judge_may_gate=True,
            regressed=True,
            broken_cases=(),
            error_budget_spent=False,
            is_fix=False,
            dataset_usable=True,
        )
