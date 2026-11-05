"""Putting back what a run changed, in the right order."""

from __future__ import annotations

import pytest

from agent.src.agent.undo import Change, Outcome, plan_undo, summarise_undo


def change(order: int, **kwargs) -> Change:
    defaults = {
        "target": f"thing-{order}",
        "kind": "file-written",
        "reversible": True,
        "order": order,
    }
    defaults.update(kwargs)
    return Change(**defaults)


def test_changes_are_undone_newest_first():
    steps = plan_undo([change(1), change(2), change(3)]).steps
    assert [step.order for step in steps] == [3, 2, 1]


def test_only_reversible_changes_are_undone():
    steps = plan_undo([change(1), change(2, reversible=False)]).steps
    assert [step.order for step in steps] == [1]


def test_what_cannot_be_undone_is_listed_rather_than_dropped():
    plan = plan_undo([change(1), change(2, reversible=False, target="email")])
    assert plan.cannot_undo == ("email",)


def test_a_plan_that_can_undo_everything_says_so():
    assert plan_undo([change(1), change(2)]).complete is True


def test_a_plan_leaving_something_behind_is_not_complete():
    assert plan_undo([change(1, reversible=False)]).complete is False


def test_undoing_nothing_is_refused():
    with pytest.raises(ValueError):
        plan_undo([])


def test_a_plan_of_only_permanent_changes_has_no_steps():
    assert plan_undo([change(1, reversible=False)]).steps == ()


def test_two_changes_to_the_same_thing_are_undone_once():
    steps = plan_undo([change(1, target="file"), change(2, target="file")]).steps
    assert len(steps) == 1


def test_the_newest_change_to_a_thing_is_the_one_undone():
    steps = plan_undo([change(1, target="file"), change(2, target="file")]).steps
    assert steps[0].order == 2


def test_an_undo_that_worked_is_reported_as_done():
    results = {"thing-1": Outcome.UNDONE}
    assert summarise_undo(results).all_undone is True


def test_an_undo_that_failed_is_reported():
    results = {"thing-1": Outcome.UNDONE, "thing-2": Outcome.FAILED}
    assert summarise_undo(results).failed == ("thing-2",)


def test_a_partial_undo_is_not_reported_as_done():
    results = {"thing-1": Outcome.UNDONE, "thing-2": Outcome.FAILED}
    assert summarise_undo(results).all_undone is False


def test_something_already_back_as_it_was_is_not_a_failure():
    results = {"thing-1": Outcome.UNDONE, "thing-2": Outcome.ALREADY_GONE}
    assert summarise_undo(results).all_undone is True


def test_the_summary_reads_plainly():
    results = {"a": Outcome.UNDONE, "b": Outcome.FAILED, "c": Outcome.ALREADY_GONE}
    assert (
        summarise_undo(results).message
        == "1 undone, 1 already gone, 1 could not be undone"
    )


def test_a_failed_undo_leaves_the_world_half_changed_and_says_so():
    results = {"a": Outcome.UNDONE, "b": Outcome.FAILED}
    assert "partly" in summarise_undo(results).warning


def test_a_complete_undo_carries_no_warning():
    assert summarise_undo({"a": Outcome.UNDONE}).warning == ""


def test_summarising_nothing_is_refused():
    with pytest.raises(ValueError):
        summarise_undo({})


def test_a_change_without_a_target_is_refused():
    with pytest.raises(ValueError):
        change(1, target="  ")
