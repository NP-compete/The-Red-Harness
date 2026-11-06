"""Moving a new agent version into service a bit at a time."""

from __future__ import annotations

import pytest

from agent.src.security.rollout import Health, Rollout, Step, advance

HEALTHY = Health(
    runs=200, failure_rate=0.01, refusal_rate=0.02, baseline_failure_rate=0.01
)


def rollout(**kwargs) -> Rollout:
    defaults = {
        "version": "4.2",
        "previous_version": "4.1",
        "share": 0.0,
        "steps": (0.05, 0.25, 1.0),
        "halted": False,
    }
    defaults.update(kwargs)
    return Rollout(**defaults)


def test_a_new_version_starts_on_a_small_share():
    assert advance(rollout(), HEALTHY).share == 0.05


def test_a_healthy_version_moves_to_the_next_step():
    assert advance(rollout(share=0.05), HEALTHY).share == 0.25


def test_a_version_that_finishes_every_step_is_fully_live():
    assert advance(rollout(share=0.25), HEALTHY).step is Step.COMPLETE


def test_a_completed_rollout_serves_everyone():
    assert advance(rollout(share=0.25), HEALTHY).share == 1.0


def test_too_few_runs_is_not_evidence_of_health():
    thin = Health(
        runs=3, failure_rate=0.0, refusal_rate=0.0, baseline_failure_rate=0.01
    )
    assert advance(rollout(share=0.05), thin).step is Step.WAITING


def test_waiting_says_it_needs_more_runs():
    thin = Health(
        runs=3, failure_rate=0.0, refusal_rate=0.0, baseline_failure_rate=0.01
    )
    assert "more runs" in advance(rollout(share=0.05), thin).reason


def test_waiting_does_not_move_the_share():
    thin = Health(
        runs=3, failure_rate=0.0, refusal_rate=0.0, baseline_failure_rate=0.01
    )
    assert advance(rollout(share=0.05), thin).share == 0.05


def test_a_version_failing_worse_than_the_old_one_is_rolled_back():
    worse = Health(
        runs=200, failure_rate=0.08, refusal_rate=0.02, baseline_failure_rate=0.01
    )
    assert advance(rollout(share=0.05), worse).step is Step.ROLLED_BACK


def test_a_rollback_returns_every_run_to_the_old_version():
    worse = Health(
        runs=200, failure_rate=0.08, refusal_rate=0.02, baseline_failure_rate=0.01
    )
    assert advance(rollout(share=0.25), worse).share == 0.0


def test_a_rollback_names_the_version_being_served_again():
    worse = Health(
        runs=200, failure_rate=0.08, refusal_rate=0.02, baseline_failure_rate=0.01
    )
    assert "4.1" in advance(rollout(share=0.25), worse).reason


def test_a_small_rise_in_failures_is_tolerated():
    slightly_worse = Health(
        runs=200, failure_rate=0.015, refusal_rate=0.02, baseline_failure_rate=0.01
    )
    assert advance(rollout(share=0.05), slightly_worse).step is Step.ADVANCED


def test_a_surge_of_refusals_also_rolls_back():
    refusing = Health(
        runs=200, failure_rate=0.01, refusal_rate=0.4, baseline_failure_rate=0.01
    )
    assert advance(rollout(share=0.05), refusing).step is Step.ROLLED_BACK


def test_a_halted_rollout_does_not_advance_on_its_own():
    assert advance(rollout(share=0.05, halted=True), HEALTHY).step is Step.HALTED


def test_a_halted_rollout_holds_its_current_share():
    assert advance(rollout(share=0.05, halted=True), HEALTHY).share == 0.05


def test_a_halted_rollout_can_still_be_rolled_back_by_bad_health():
    worse = Health(
        runs=200, failure_rate=0.08, refusal_rate=0.02, baseline_failure_rate=0.01
    )
    assert advance(rollout(share=0.05, halted=True), worse).step is Step.ROLLED_BACK


def test_a_rollout_with_no_steps_is_refused():
    with pytest.raises(ValueError):
        rollout(steps=())


@pytest.mark.parametrize("steps", [(0.5, 0.25), (0.5, 1.5)])
def test_steps_that_do_not_climb_to_everyone_are_refused(steps):
    with pytest.raises(ValueError):
        rollout(steps=steps)


def test_a_version_cannot_replace_itself():
    with pytest.raises(ValueError):
        rollout(previous_version="4.2")
