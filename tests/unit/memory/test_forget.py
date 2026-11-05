"""Carrying out a request to forget something, and saying what that cannot undo."""

from __future__ import annotations

import pytest

from agent.src.memory.forget import Held, plan_forget


def held(**kwargs) -> Held:
    defaults = {
        "key": "units",
        "text": "Metric units in every report.",
        "topic": "formatting",
        "owner": "ada",
        "used_in_sent_message": False,
        "shared_with_team": False,
    }
    defaults.update(kwargs)
    return Held(**defaults)


def test_a_memory_named_outright_is_forgotten():
    plan = plan_forget([held()], asked_by="ada", about="units")
    assert plan.forgetting == ["units"]


def test_a_memory_on_the_named_topic_is_forgotten():
    plan = plan_forget([held()], asked_by="ada", about="formatting")
    assert plan.forgetting == ["units"]


def test_a_memory_on_another_topic_is_left_alone():
    plan = plan_forget([held()], asked_by="ada", about="travel")
    assert plan.forgetting == []


def test_someone_else_s_memory_is_never_forgotten_on_your_say_so():
    theirs = held(owner="grace", shared_with_team=True)
    plan = plan_forget([theirs], asked_by="ada", about="units")
    assert plan.forgetting == []


def test_a_request_touching_someone_else_s_memory_says_why_it_could_not():
    theirs = held(owner="grace", shared_with_team=True)
    plan = plan_forget([theirs], asked_by="ada", about="units")
    assert plan.untouched == ["units"]


def test_everything_about_a_person_can_be_forgotten_at_once():
    all_of_it = [held(key="units"), held(key="tone", topic="style")]
    plan = plan_forget(all_of_it, asked_by="ada", about="")
    assert plan.forgetting == ["units", "tone"]


def test_a_memory_already_used_in_a_sent_message_is_still_forgotten():
    sent = held(used_in_sent_message=True)
    plan = plan_forget([sent], asked_by="ada", about="units")
    assert plan.forgetting == ["units"]


def test_a_memory_already_used_is_reported_as_something_that_cannot_be_unsaid():
    sent = held(used_in_sent_message=True)
    plan = plan_forget([sent], asked_by="ada", about="units")
    assert plan.cannot_unsay == ["units"]


def test_a_memory_never_used_leaves_nothing_behind():
    plan = plan_forget([held()], asked_by="ada", about="units")
    assert plan.cannot_unsay == []


def test_forgetting_nothing_is_reported_plainly():
    plan = plan_forget([held()], asked_by="ada", about="travel")
    assert plan.found_nothing is True


def test_forgetting_something_is_not_reported_as_nothing():
    plan = plan_forget([held()], asked_by="ada", about="units")
    assert plan.found_nothing is False


def test_a_memory_shared_with_the_team_is_forgotten_for_everyone():
    shared = held(shared_with_team=True)
    plan = plan_forget([shared], asked_by="ada", about="units")
    assert plan.affects_others == ["units"]


def test_a_private_memory_affects_nobody_else():
    plan = plan_forget([held()], asked_by="ada", about="units")
    assert plan.affects_others == []


def test_a_plan_that_affects_others_is_confirmed_first():
    shared = held(shared_with_team=True)
    plan = plan_forget([shared], asked_by="ada", about="units")
    assert plan.needs_confirmation is True


def test_a_plan_touching_only_your_own_memories_needs_no_confirming():
    plan = plan_forget([held()], asked_by="ada", about="units")
    assert plan.needs_confirmation is False


def test_a_request_from_nobody_is_refused():
    with pytest.raises(ValueError):
        plan_forget([held()], asked_by="  ", about="units")
