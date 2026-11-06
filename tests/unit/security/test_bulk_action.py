"""Doing the same thing to many items without losing track of what happened."""

from __future__ import annotations

import pytest

from agent.src.security.bulk_action import Outcome, plan_bulk, summarise_bulk


def test_a_small_bulk_action_needs_no_confirmation():
    assert plan_bulk(["a", "b"], action="archive").needs_confirmation is False


def test_a_large_bulk_action_needs_confirmation():
    assert (
        plan_bulk([str(n) for n in range(50)], action="archive").needs_confirmation
        is True
    )


def test_any_deletion_needs_confirmation():
    assert plan_bulk(["a"], action="delete").needs_confirmation is True


def test_the_confirmation_says_how_many_and_what():
    plan = plan_bulk(["a", "b"], action="delete")
    assert "2" in plan.confirmation and "delete" in plan.confirmation


def test_an_empty_selection_has_nothing_to_do():
    assert plan_bulk([], action="archive").runnable is False


def test_an_empty_selection_says_so():
    assert "nothing" in plan_bulk([], action="archive").reason


def test_duplicates_in_the_selection_are_collapsed():
    assert plan_bulk(["a", "a", "b"], action="archive").items == ("a", "b")


def test_a_selection_beyond_the_ceiling_is_refused():
    assert plan_bulk([str(n) for n in range(5_000)], action="archive").runnable is False


def test_a_refused_selection_says_what_the_ceiling_is():
    plan = plan_bulk([str(n) for n in range(5_000)], action="archive")
    assert "1000" in plan.reason


def test_the_plan_reports_how_many_will_be_touched():
    assert plan_bulk(["a", "b", "c"], action="archive").count == 3


def test_results_are_summarised_by_what_happened():
    results = {"a": Outcome.DONE, "b": Outcome.DONE, "c": Outcome.FAILED}
    assert summarise_bulk(results).done == 2


def test_failures_are_counted():
    results = {"a": Outcome.DONE, "c": Outcome.FAILED}
    assert summarise_bulk(results).failed == 1


def test_items_that_were_skipped_are_counted_separately_from_failures():
    results = {"a": Outcome.DONE, "b": Outcome.SKIPPED, "c": Outcome.FAILED}
    summary = summarise_bulk(results)
    assert summary.skipped == 1 and summary.failed == 1


def test_the_failures_are_named_so_they_can_be_retried():
    results = {"a": Outcome.DONE, "c": Outcome.FAILED, "d": Outcome.FAILED}
    assert summarise_bulk(results).failed_items == ("c", "d")


def test_a_partial_failure_is_not_reported_as_success():
    results = {"a": Outcome.DONE, "c": Outcome.FAILED}
    assert summarise_bulk(results).all_succeeded is False


def test_everything_working_is_reported_as_success():
    assert summarise_bulk({"a": Outcome.DONE}).all_succeeded is True


def test_a_summary_says_plainly_what_happened():
    results = {"a": Outcome.DONE, "b": Outcome.DONE, "c": Outcome.FAILED}
    assert summarise_bulk(results).message == "2 done, 1 failed"


def test_a_summary_mentions_skipped_items_when_there_are_any():
    results = {"a": Outcome.DONE, "b": Outcome.SKIPPED}
    assert summarise_bulk(results).message == "1 done, 1 skipped"


def test_an_empty_result_set_is_refused():
    with pytest.raises(ValueError):
        summarise_bulk({})


def test_an_action_without_a_name_is_refused():
    with pytest.raises(ValueError):
        plan_bulk(["a"], action=" ")
