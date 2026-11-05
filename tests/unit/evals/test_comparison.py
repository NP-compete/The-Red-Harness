"""Comparing how two versions did on the same cases."""

from __future__ import annotations

import pytest

from agent.src.evals.comparison import Case, Verdict, compare_runs


def cases(**outcomes) -> list[Case]:
    return [
        Case(case_id=name, before=before, after=after)
        for name, (before, after) in outcomes.items()
    ]


def test_identical_results_are_no_change():
    result = compare_runs(cases(a=(True, True), b=(False, False)))
    assert result.verdict is Verdict.NO_CHANGE


def test_a_case_that_started_passing_is_an_improvement():
    assert compare_runs(cases(a=(False, True))).fixed == ("a",)


def test_a_case_that_stopped_passing_is_a_regression():
    assert compare_runs(cases(a=(True, False))).broken == ("a",)


def test_any_regression_makes_the_whole_comparison_a_regression():
    result = compare_runs(
        cases(a=(True, False), b=(False, True), c=(False, True), d=(False, True))
    )
    assert result.verdict is Verdict.REGRESSED


def test_improvements_without_regressions_are_an_improvement():
    assert (
        compare_runs(cases(a=(False, True), b=(True, True))).verdict is Verdict.IMPROVED
    )


def test_the_counts_are_reported():
    result = compare_runs(cases(a=(True, False), b=(False, True), c=(True, True)))
    assert (len(result.broken), len(result.fixed)) == (1, 1)


def test_the_pass_rates_are_reported():
    result = compare_runs(
        cases(a=(True, True), b=(True, False), c=(False, False), d=(True, True))
    )
    assert (result.before_rate, result.after_rate) == (0.75, 0.5)


def test_broken_cases_are_named_so_they_can_be_looked_at():
    result = compare_runs(cases(z=(True, False), a=(True, False)))
    assert result.broken == ("a", "z")


def test_a_comparison_with_no_cases_is_refused():
    with pytest.raises(ValueError):
        compare_runs([])


def test_a_case_appearing_twice_is_refused():
    duplicated = [
        Case(case_id="a", before=True, after=True),
        Case(case_id="a", before=False, after=False),
    ]
    with pytest.raises(ValueError):
        compare_runs(duplicated)


def test_a_small_sample_does_not_claim_an_improvement():
    result = compare_runs(cases(a=(False, True)), min_cases=10)
    assert result.verdict is Verdict.INCONCLUSIVE


def test_a_small_sample_still_reports_a_regression():
    result = compare_runs(cases(a=(True, False)), min_cases=10)
    assert result.verdict is Verdict.REGRESSED


def test_an_inconclusive_comparison_says_how_many_more_are_needed():
    result = compare_runs(cases(a=(False, True)), min_cases=10)
    assert "10" in result.reason


def test_a_regression_is_never_called_inconclusive_however_few_the_cases():
    result = compare_runs(cases(a=(True, False)), min_cases=100)
    assert result.verdict is Verdict.REGRESSED


def test_the_summary_reads_plainly():
    result = compare_runs(cases(a=(True, False), b=(False, True)))
    assert result.summary == "1 broke, 1 fixed"


def test_the_summary_of_no_change_says_so():
    assert compare_runs(cases(a=(True, True))).summary == "nothing changed"
