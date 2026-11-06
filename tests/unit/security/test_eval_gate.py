"""Deciding whether a change may ship, from the checks that ran."""

from __future__ import annotations

import pytest

from agent.src.security.eval_gate import CheckResult, decide

BASELINE = {
    "injection-resistance": 0.97,
    "citation-grounding": 0.78,
    "scope-leakage": 1.0,
}


def results(**overrides) -> list[CheckResult]:
    scores = {**BASELINE, **overrides}
    return [
        CheckResult(name=name, score=score, blocking=name != "citation-grounding")
        for name, score in scores.items()
    ]


BLOCKING = {"injection-resistance", "scope-leakage"}


def gate(**kwargs):
    kwargs.setdefault("results", results())
    kwargs.setdefault("baseline", BASELINE)
    kwargs.setdefault("blocking", BLOCKING)
    return decide(**kwargs)


def test_unchanged_scores_ship():
    assert gate().ok is True


def test_an_improvement_ships():
    assert gate(results=results(**{"injection-resistance": 0.99})).ok is True


def test_a_regression_in_a_blocking_check_stops_the_change():
    assert gate(results=results(**{"injection-resistance": 0.80})).ok is False


def test_the_blocked_check_is_named():
    decision = gate(results=results(**{"injection-resistance": 0.80}))
    assert "injection-resistance" in decision.blocked_by


def test_a_regression_in_a_non_blocking_check_still_ships():
    assert gate(results=results(**{"citation-grounding": 0.50})).ok is True


def test_a_non_blocking_regression_is_still_reported():
    decision = gate(results=results(**{"citation-grounding": 0.50}))
    assert "citation-grounding" in decision.regressions


def test_a_tiny_movement_is_treated_as_noise():
    assert gate(results=results(**{"injection-resistance": 0.969})).ok is True


def test_the_noise_floor_can_be_tightened():
    decision = gate(results=results(**{"injection-resistance": 0.969}), tolerance=0.0)
    assert decision.ok is False


def test_a_check_with_no_baseline_cannot_regress():
    extra = [*results(), CheckResult(name="brand-new", score=0.1, blocking=True)]
    assert gate(results=extra).ok is True


def test_a_missing_check_is_treated_as_a_failure_to_run():
    partial = [r for r in results() if r.name != "scope-leakage"]
    decision = gate(results=partial)
    assert decision.ok is False
    assert "scope-leakage" in decision.missing


def test_a_missing_non_blocking_check_does_not_stop_the_change():
    partial = [r for r in results() if r.name != "citation-grounding"]
    assert gate(results=partial).ok is True


@pytest.mark.parametrize("tolerance", [-0.1, -1])
def test_a_nonsense_tolerance_is_refused(tolerance):
    with pytest.raises(ValueError):
        gate(tolerance=tolerance)
