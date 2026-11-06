"""Bringing stored conversation state up to the version in use."""

from __future__ import annotations

import pytest

from agent.src.agent.state_migration import Outcome, Step, migrate

STEPS = (
    Step(from_version=1, to_version=2, adds=("title",), removes=()),
    Step(from_version=2, to_version=3, adds=("tags",), removes=("legacy_flag",)),
)


def test_state_already_current_is_left_alone():
    state = {"version": 3, "title": "x", "tags": []}
    assert migrate(state, to_version=3, steps=STEPS).outcome is Outcome.ALREADY_CURRENT


def test_state_already_current_comes_back_unchanged():
    state = {"version": 3, "title": "x"}
    assert migrate(state, to_version=3, steps=STEPS).state == state


def test_one_step_behind_is_brought_forward():
    state = {"version": 2, "title": "x", "legacy_flag": True}
    assert migrate(state, to_version=3, steps=STEPS).state["version"] == 3


def test_a_field_the_new_version_needs_is_added():
    state = {"version": 2, "title": "x"}
    assert "tags" in migrate(state, to_version=3, steps=STEPS).state


def test_a_field_the_new_version_dropped_is_removed():
    state = {"version": 2, "legacy_flag": True}
    assert "legacy_flag" not in migrate(state, to_version=3, steps=STEPS).state


def test_several_steps_are_applied_in_order():
    state = {"version": 1}
    migrated = migrate(state, to_version=3, steps=STEPS).state
    assert migrated["version"] == 3 and "title" in migrated and "tags" in migrated


def test_what_was_done_is_reported():
    state = {"version": 1}
    assert migrate(state, to_version=3, steps=STEPS).applied == (2, 3)


def test_nothing_is_reported_when_nothing_was_needed():
    assert migrate({"version": 3}, to_version=3, steps=STEPS).applied == ()


def test_existing_values_are_not_overwritten():
    state = {"version": 2, "tags": ["kept"]}
    assert migrate(state, to_version=3, steps=STEPS).state["tags"] == ["kept"]


def test_the_original_is_not_changed():
    state = {"version": 2, "legacy_flag": True}
    migrate(state, to_version=3, steps=STEPS)
    assert state["legacy_flag"] is True


def test_state_from_a_newer_version_is_not_touched():
    state = {"version": 9, "unknown": True}
    assert migrate(state, to_version=3, steps=STEPS).outcome is Outcome.TOO_NEW


def test_state_from_a_newer_version_comes_back_as_it_was():
    state = {"version": 9, "unknown": True}
    assert migrate(state, to_version=3, steps=STEPS).state == state


def test_state_too_old_to_bring_forward_is_reported():
    state = {"version": 0}
    assert migrate(state, to_version=3, steps=STEPS).outcome is Outcome.NO_PATH


def test_state_with_no_path_is_left_as_it_was():
    state = {"version": 0, "something": 1}
    assert migrate(state, to_version=3, steps=STEPS).state == state


def test_a_migrated_state_says_it_was_migrated():
    assert (
        migrate({"version": 1}, to_version=3, steps=STEPS).outcome is Outcome.MIGRATED
    )


def test_state_without_a_version_is_refused():
    with pytest.raises(ValueError):
        migrate({}, to_version=3, steps=STEPS)


def test_a_step_that_goes_backwards_is_refused():
    with pytest.raises(ValueError):
        Step(from_version=3, to_version=2, adds=(), removes=())


def test_two_steps_from_the_same_version_are_refused():
    clashing = (
        Step(from_version=1, to_version=2, adds=(), removes=()),
        Step(from_version=1, to_version=3, adds=(), removes=()),
    )
    with pytest.raises(ValueError):
        migrate({"version": 1}, to_version=3, steps=clashing)
