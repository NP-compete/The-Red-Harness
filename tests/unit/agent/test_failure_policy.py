"""What the rest of a plan does when one task fails."""

from __future__ import annotations

import pytest

from agent.src.agent.failure_policy import Fate, Task, after_failure


def task(name: str, needs: tuple[str, ...] = (), optional: bool = False) -> Task:
    return Task(name=name, needs=needs, optional=optional)


PLAN = [
    task("gather"),
    task("summarise", needs=("gather",)),
    task("publish", needs=("summarise",)),
    task("notify", optional=True),
]


def test_a_task_that_failed_is_marked_failed():
    assert after_failure(PLAN, failed="gather").fates["gather"] is Fate.FAILED


def test_anything_waiting_on_it_cannot_run():
    assert after_failure(PLAN, failed="gather").fates["summarise"] is Fate.SKIPPED


def test_anything_waiting_further_down_cannot_run_either():
    assert after_failure(PLAN, failed="gather").fates["publish"] is Fate.SKIPPED


def test_unrelated_work_carries_on():
    assert after_failure(PLAN, failed="gather").fates["notify"] is Fate.CONTINUES


def test_the_run_is_not_abandoned_when_something_can_still_be_done():
    assert after_failure(PLAN, failed="gather").abandon is False


def test_the_run_is_abandoned_when_nothing_is_left_to_do():
    plan = [task("gather"), task("summarise", needs=("gather",))]
    assert after_failure(plan, failed="gather").abandon is True


def test_an_optional_task_failing_does_not_stop_anything():
    assert after_failure(PLAN, failed="notify").abandon is False


def test_an_optional_task_failing_leaves_the_rest_alone():
    fates = after_failure(PLAN, failed="notify").fates
    assert fates["gather"] is Fate.CONTINUES


def test_what_was_lost_is_counted():
    assert after_failure(PLAN, failed="gather").skipped == ("publish", "summarise")


def test_nothing_is_lost_when_an_optional_task_fails():
    assert after_failure(PLAN, failed="notify").skipped == ()


def test_the_reason_names_the_task_that_failed():
    assert "gather" in after_failure(PLAN, failed="gather").reason


def test_a_partial_result_is_offered_when_some_work_finished():
    plan = [task("a"), task("b"), task("c", needs=("b",))]
    assert after_failure(plan, failed="b").partial_result is True


def test_no_partial_result_is_offered_when_everything_is_lost():
    plan = [task("a"), task("b", needs=("a",))]
    assert after_failure(plan, failed="a").partial_result is False


def test_an_optional_dependency_does_not_block_its_dependents():
    plan = [task("enrich", optional=True), task("write", needs=("enrich",))]
    assert after_failure(plan, failed="enrich").fates["write"] is Fate.CONTINUES


def test_failing_something_not_in_the_plan_is_refused():
    with pytest.raises(ValueError):
        after_failure(PLAN, failed="nonexistent")


def test_an_empty_plan_is_refused():
    with pytest.raises(ValueError):
        after_failure([], failed="a")
