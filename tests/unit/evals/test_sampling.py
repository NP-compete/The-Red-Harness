"""Choosing which runs a person should look at."""

from __future__ import annotations

import pytest

from agent.src.evals.sampling import Run, choose_sample


def runs(**counts) -> list[Run]:
    made: list[Run] = []
    for outcome, count in counts.items():
        for index in range(count):
            made.append(
                Run(
                    run_id=f"{outcome}-{index}",
                    outcome=outcome,
                    reviewed=False,
                    rated_down=False,
                )
            )
    return made


def test_a_sample_is_the_size_asked_for():
    assert len(choose_sample(runs(ok=100), size=10, seed=1)) == 10


def test_a_sample_cannot_be_larger_than_what_there_is():
    assert len(choose_sample(runs(ok=5), size=10, seed=1)) == 5


def test_the_same_seed_gives_the_same_sample():
    first = choose_sample(runs(ok=100), size=10, seed=1)
    second = choose_sample(runs(ok=100), size=10, seed=1)
    assert [run.run_id for run in first] == [run.run_id for run in second]


def test_a_different_seed_gives_a_different_sample():
    first = choose_sample(runs(ok=100), size=10, seed=1)
    second = choose_sample(runs(ok=100), size=10, seed=2)
    assert [run.run_id for run in first] != [run.run_id for run in second]


def test_failures_are_represented_even_though_they_are_rare():
    sample = choose_sample(runs(ok=990, failed=10), size=10, seed=1)
    assert any(run.outcome == "failed" for run in sample)


def test_runs_people_disliked_are_represented():
    population = runs(ok=100)
    population[0] = Run(run_id="sad", outcome="ok", reviewed=False, rated_down=True)
    sample = choose_sample(population, size=5, seed=1)
    assert any(run.run_id == "sad" for run in sample)


def test_ordinary_runs_are_still_included():
    sample = choose_sample(runs(ok=90, failed=10), size=10, seed=1)
    assert any(run.outcome == "ok" for run in sample)


def test_a_run_already_reviewed_is_not_chosen_again():
    population = [
        Run(run_id="seen", outcome="failed", reviewed=True, rated_down=False),
        *runs(ok=10),
    ]
    sample = choose_sample(population, size=5, seed=1)
    assert all(run.run_id != "seen" for run in sample)


def test_a_sample_never_repeats_a_run():
    sample = choose_sample(runs(ok=20, failed=5), size=15, seed=1)
    assert len({run.run_id for run in sample}) == len(sample)


def test_a_population_of_only_reviewed_runs_yields_nothing():
    population = [Run(run_id="seen", outcome="ok", reviewed=True, rated_down=False)]
    assert choose_sample(population, size=5, seed=1) == []


def test_an_empty_population_yields_nothing():
    assert choose_sample([], size=5, seed=1) == []


def test_asking_for_nothing_yields_nothing():
    assert choose_sample(runs(ok=10), size=0, seed=1) == []


def test_a_negative_size_is_refused():
    with pytest.raises(ValueError):
        choose_sample(runs(ok=10), size=-1, seed=1)


def test_the_sample_is_returned_in_a_stable_order():
    sample = choose_sample(runs(ok=50, failed=10), size=10, seed=3)
    assert [run.run_id for run in sample] == sorted(run.run_id for run in sample)
