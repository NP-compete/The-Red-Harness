"""Telling a real change in scores apart from ordinary noise."""

from __future__ import annotations

import pytest

from agent.src.evals.drift import Movement, Run, detect_drift


def runs(*scores: float) -> list[Run]:
    return [Run(run=f"r{i}", score=score, cases=50) for i, score in enumerate(scores)]


def test_scores_holding_steady_are_called_steady():
    history = runs(0.80, 0.81, 0.79, 0.80, 0.81, 0.80)
    assert detect_drift(history, baseline=0.80).movement is Movement.STEADY


def test_a_sustained_fall_is_called_a_fall():
    history = runs(0.80, 0.79, 0.70, 0.69, 0.68, 0.67)
    assert detect_drift(history, baseline=0.80).movement is Movement.FALLING


def test_a_sustained_rise_is_called_a_rise():
    history = runs(0.70, 0.71, 0.80, 0.82, 0.84, 0.85)
    assert detect_drift(history, baseline=0.70).movement is Movement.RISING


def test_one_bad_run_among_good_ones_is_not_a_fall():
    history = runs(0.80, 0.81, 0.62, 0.80, 0.81, 0.80)
    assert detect_drift(history, baseline=0.80).movement is Movement.STEADY


def test_a_single_dip_is_still_reported_as_an_outlier():
    history = runs(0.80, 0.81, 0.62, 0.80, 0.81, 0.80)
    assert detect_drift(history, baseline=0.80).outliers == ["r2"]


def test_a_steady_run_of_scores_has_no_outliers():
    history = runs(0.80, 0.81, 0.79, 0.80, 0.81, 0.80)
    assert detect_drift(history, baseline=0.80).outliers == []


def test_how_far_from_the_baseline_things_have_moved_is_reported():
    history = runs(0.70, 0.70, 0.70, 0.70)
    assert detect_drift(history, baseline=0.80).gap == pytest.approx(-0.10)


def test_a_rise_is_reported_as_a_positive_gap():
    history = runs(0.90, 0.90, 0.90, 0.90)
    assert detect_drift(history, baseline=0.80).gap == pytest.approx(0.10)


def test_too_few_runs_to_say_anything_says_so():
    assert detect_drift(runs(0.80, 0.60), baseline=0.80).movement is Movement.UNKNOWN


def test_too_few_runs_is_not_called_steady():
    assert detect_drift(runs(0.80), baseline=0.80).movement is not Movement.STEADY


def test_a_fall_is_worth_someone_looking():
    history = runs(0.80, 0.79, 0.70, 0.69, 0.68, 0.67)
    assert detect_drift(history, baseline=0.80).needs_attention is True


def test_a_rise_is_not_something_to_chase():
    history = runs(0.70, 0.71, 0.80, 0.82, 0.84, 0.85)
    assert detect_drift(history, baseline=0.70).needs_attention is False


def test_a_run_over_too_few_cases_is_not_counted():
    thin = [Run(run="r0", score=0.1, cases=1)] + runs(0.80, 0.81, 0.79, 0.80, 0.81)
    assert detect_drift(thin, baseline=0.80).movement is Movement.STEADY


def test_no_history_at_all_says_nothing():
    assert detect_drift([], baseline=0.80).movement is Movement.UNKNOWN


def test_a_score_outside_its_range_is_refused():
    with pytest.raises(ValueError):
        Run(run="r0", score=1.2, cases=10)


def test_a_baseline_outside_its_range_is_refused():
    with pytest.raises(ValueError):
        detect_drift(runs(0.8), baseline=-0.1)
