"""Benchmark results, traceable to the configuration that earned them."""

from __future__ import annotations

import pytest

from agent.src.evals.results import Result, ResultsStore


def result(**kwargs) -> Result:
    defaults = {
        "fingerprint": "cfg_7b19e4",
        "suite": "professional",
        "model": "large",
        "score": 0.71,
        "tasks": 120,
        "variance": 0.03,
        "approvals_per_run": 1.2,
    }
    defaults.update(kwargs)
    return Result(**defaults)


@pytest.fixture()
def store(tmp_path) -> ResultsStore:
    return ResultsStore(tmp_path / "results.jsonl")


def test_a_recorded_result_can_be_read_back(store):
    store.record(result())
    assert store.all()[0].score == 0.71


def test_results_are_appended_rather_than_replaced(store):
    store.record(result())
    store.record(result(score=0.76, fingerprint="cfg_other"))
    assert len(store.all()) == 2


def test_a_rerun_of_the_same_configuration_is_kept_too(store):
    store.record(result(score=0.70))
    store.record(result(score=0.72))
    assert [r.score for r in store.all()] == [0.70, 0.72]


def test_a_result_must_name_the_configuration_that_earned_it(store):
    with pytest.raises(ValueError):
        result(fingerprint="")


def test_a_score_without_a_task_count_is_refused(store):
    with pytest.raises(ValueError):
        result(tasks=0)


def test_two_configurations_can_be_compared(store):
    store.record(result(fingerprint="a", score=0.71))
    store.record(result(fingerprint="b", score=0.76))
    delta = store.compare("a", "b", suite="professional")
    assert delta.difference == pytest.approx(0.05)


def test_a_comparison_says_whether_the_difference_clears_the_noise(store):
    store.record(result(fingerprint="a", score=0.71, variance=0.03))
    store.record(result(fingerprint="b", score=0.76, variance=0.03))
    assert store.compare("a", "b", suite="professional").significant is True


def test_a_difference_inside_the_variance_is_not_significant(store):
    store.record(result(fingerprint="a", score=0.71, variance=0.05))
    store.record(result(fingerprint="b", score=0.73, variance=0.05))
    assert store.compare("a", "b", suite="professional").significant is False


def test_comparing_across_suites_is_refused(store):
    store.record(result(fingerprint="a", suite="professional"))
    store.record(result(fingerprint="b", suite="long-horizon"))
    with pytest.raises(LookupError):
        store.compare("a", "b", suite="professional")


def test_the_latest_run_of_a_configuration_is_the_one_compared(store):
    store.record(result(fingerprint="a", score=0.50))
    store.record(result(fingerprint="a", score=0.71))
    store.record(result(fingerprint="b", score=0.76))
    assert store.compare("a", "b", suite="professional").difference == pytest.approx(
        0.05
    )
