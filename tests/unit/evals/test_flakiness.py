"""Finding cases that do not give the same answer twice."""

from __future__ import annotations

import pytest

from agent.src.evals.flakiness import Attempt, Stability, assess_flakiness


def attempts(case_id: str, *outcomes: bool) -> list[Attempt]:
    return [
        Attempt(case_id=case_id, run=index, passed=outcome)
        for index, outcome in enumerate(outcomes)
    ]


def test_a_case_that_always_passes_is_steady():
    result = assess_flakiness(attempts("a", True, True, True))
    assert result.cases["a"].stability is Stability.STEADY


def test_a_case_that_always_fails_is_steady_too():
    result = assess_flakiness(attempts("a", False, False, False))
    assert result.cases["a"].stability is Stability.STEADY


def test_a_case_that_always_fails_is_marked_as_failing():
    result = assess_flakiness(attempts("a", False, False, False))
    assert result.cases["a"].passes is False


def test_a_case_that_sometimes_passes_is_flaky():
    result = assess_flakiness(attempts("a", True, False, True))
    assert result.cases["a"].stability is Stability.FLAKY


def test_how_often_a_flaky_case_passes_is_reported():
    result = assess_flakiness(attempts("a", True, False, True, True))
    assert result.cases["a"].pass_rate == 0.75


def test_a_case_tried_only_once_is_unknown():
    result = assess_flakiness(attempts("a", True))
    assert result.cases["a"].stability is Stability.UNKNOWN


def test_a_case_tried_only_once_says_how_many_more_are_needed():
    result = assess_flakiness(attempts("a", True))
    assert "3" in result.cases["a"].reason


def test_flaky_cases_are_listed_together():
    runs = [*attempts("a", True, True, True), *attempts("b", True, False, True)]
    assert assess_flakiness(runs).flaky == ("b",)


def test_a_steady_case_is_not_listed_as_flaky():
    assert assess_flakiness(attempts("a", True, True, True)).flaky == ()


def test_how_much_of_the_suite_is_flaky_is_reported():
    runs = [*attempts("a", True, True, True), *attempts("b", True, False, True)]
    assert assess_flakiness(runs).flaky_share == 0.5


def test_a_suite_with_flaky_cases_cannot_be_trusted_to_gate():
    runs = [*attempts("a", True, True, True), *attempts("b", True, False, True)]
    assert assess_flakiness(runs).may_gate is False


def test_a_steady_suite_may_gate():
    runs = [*attempts("a", True, True, True), *attempts("b", False, False, False)]
    assert assess_flakiness(runs).may_gate is True


def test_a_suite_with_unknown_cases_may_not_gate_either():
    runs = [*attempts("a", True, True, True), *attempts("b", True)]
    assert assess_flakiness(runs).may_gate is False


def test_the_worst_offender_is_named():
    runs = [
        *attempts("a", True, False, True, True),
        *attempts("b", True, False, True, False),
    ]
    assert assess_flakiness(runs).worst == "b"


def test_nothing_is_named_when_nothing_is_flaky():
    assert assess_flakiness(attempts("a", True, True, True)).worst == ""


def test_the_same_run_counted_twice_is_refused():
    duplicated = [
        Attempt(case_id="a", run=1, passed=True),
        Attempt(case_id="a", run=1, passed=False),
    ]
    with pytest.raises(ValueError):
        assess_flakiness(duplicated)


def test_assessing_nothing_is_refused():
    with pytest.raises(ValueError):
        assess_flakiness([])
