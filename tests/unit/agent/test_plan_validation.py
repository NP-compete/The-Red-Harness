"""Checking a plan holds together before any of it runs."""

from __future__ import annotations

import pytest

from agent.src.agent.plan_validation import Problem, Task, validate_plan


def task(name: str, needs: tuple[str, ...] = ()) -> Task:
    return Task(name=name, needs=needs)


def test_a_plan_in_order_is_sound():
    plan = [task("gather"), task("write", needs=("gather",))]
    assert validate_plan(plan).sound is True


def test_a_sound_plan_has_no_problems():
    plan = [task("gather"), task("write", needs=("gather",))]
    assert validate_plan(plan).problems == ()


def test_the_order_to_run_in_is_worked_out():
    plan = [task("write", needs=("gather",)), task("gather")]
    assert validate_plan(plan).order == ("gather", "write")


def test_independent_tasks_keep_a_stable_order():
    plan = [task("b"), task("a")]
    assert validate_plan(plan).order == ("a", "b")


def test_work_that_can_happen_at_the_same_time_is_grouped():
    plan = [task("a"), task("b"), task("c", needs=("a", "b"))]
    assert validate_plan(plan).stages == (("a", "b"), ("c",))


def test_a_task_needing_something_that_does_not_exist_is_caught():
    plan = [task("write", needs=("missing",))]
    assert Problem.MISSING_DEPENDENCY in validate_plan(plan).problems


def test_the_missing_thing_is_named():
    plan = [task("write", needs=("missing",))]
    assert "missing" in validate_plan(plan).detail


def test_a_plan_that_depends_on_itself_is_caught():
    plan = [task("write", needs=("write",))]
    assert Problem.CIRCULAR in validate_plan(plan).problems


def test_two_tasks_waiting_on_each_other_are_caught():
    plan = [task("a", needs=("b",)), task("b", needs=("a",))]
    assert Problem.CIRCULAR in validate_plan(plan).problems


def test_a_longer_loop_is_caught():
    plan = [task("a", needs=("c",)), task("b", needs=("a",)), task("c", needs=("b",))]
    assert Problem.CIRCULAR in validate_plan(plan).problems


def test_the_tasks_caught_in_a_loop_are_named():
    plan = [task("a", needs=("b",)), task("b", needs=("a",))]
    assert set(validate_plan(plan).detail.split()) >= {"a,", "b"}


def test_a_plan_with_a_loop_has_no_order_to_run_in():
    plan = [task("a", needs=("b",)), task("b", needs=("a",))]
    assert validate_plan(plan).order == ()


def test_the_same_task_twice_is_caught():
    plan = [task("a"), task("a")]
    assert Problem.DUPLICATE in validate_plan(plan).problems


def test_a_task_nothing_depends_on_is_fine():
    plan = [task("a"), task("b")]
    assert validate_plan(plan).sound is True


def test_how_long_the_critical_path_is_is_reported():
    plan = [task("a"), task("b", needs=("a",)), task("c", needs=("b",))]
    assert validate_plan(plan).depth == 3


def test_a_flat_plan_has_a_depth_of_one():
    assert validate_plan([task("a"), task("b")]).depth == 1


def test_an_empty_plan_is_refused():
    with pytest.raises(ValueError):
        validate_plan([])


def test_a_task_without_a_name_is_refused():
    with pytest.raises(ValueError):
        Task(name="  ", needs=())
