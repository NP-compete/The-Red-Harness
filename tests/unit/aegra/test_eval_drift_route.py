"""Turning stored eval runs into a reading of which way scores are going."""

from __future__ import annotations

import pytest

from agent.aegra.eval_drift import rows_to_runs, summarise_drift


def row(score: float, passed: int = 30, failed: int = 10, errored: int = 0, run="r1"):
    return (run, score, passed, failed, errored)


def test_a_stored_run_keeps_its_score():
    assert rows_to_runs([row(0.8)])[0].score == 0.8


def test_the_cases_a_run_covered_are_counted():
    assert rows_to_runs([row(0.8, passed=30, failed=10, errored=2)])[0].cases == 42


def test_a_run_without_a_score_is_left_out():
    assert rows_to_runs([(None, None, 1, 1, 0)]) == []


def test_runs_are_read_oldest_first():
    rows = [row(0.9, run="new"), row(0.7, run="old")]
    assert [run.run for run in rows_to_runs(rows)] == ["old", "new"]


def test_a_steady_history_is_called_steady():
    rows = [row(s) for s in (0.80, 0.81, 0.79, 0.80, 0.81, 0.80)]
    assert summarise_drift(rows, baseline=0.8)["movement"] == "steady"


def test_a_falling_history_is_called_falling():
    rows = [row(s) for s in reversed([0.80, 0.79, 0.70, 0.69, 0.68, 0.67])]
    assert summarise_drift(rows, baseline=0.8)["movement"] == "falling"


def test_a_fall_is_worth_someone_looking():
    rows = [row(s) for s in reversed([0.80, 0.79, 0.70, 0.69, 0.68, 0.67])]
    assert summarise_drift(rows, baseline=0.8)["needs_attention"] is True


def test_the_gap_from_the_baseline_is_reported():
    rows = [row(0.7) for _ in range(4)]
    assert summarise_drift(rows, baseline=0.8)["gap"] == pytest.approx(-0.1)


def test_a_single_odd_run_is_named_rather_than_folded_in():
    rows = [row(s) for s in reversed([0.80, 0.81, 0.62, 0.80, 0.81, 0.80])]
    assert summarise_drift(rows, baseline=0.8)["outliers"] == ["r1"]


def test_too_little_history_says_so():
    assert summarise_drift([row(0.8)], baseline=0.8)["movement"] == "unknown"


def test_no_history_at_all_says_so():
    assert summarise_drift([], baseline=0.8)["movement"] == "unknown"


def test_a_baseline_outside_its_range_is_refused():
    with pytest.raises(ValueError):
        summarise_drift([row(0.8)], baseline=1.5)
