"""Amending a plan when a step turns out not to be possible."""

from __future__ import annotations

import pytest

from agent.src.agent.plan_revision import Step, revise


def step(name: str, **kwargs) -> Step:
    defaults = {"name": name, "done": False, "had_effects": False, "required": True}
    defaults.update(kwargs)
    return Step(**defaults)


def plan() -> list[Step]:
    return [step("find", done=True), step("check"), step("send")]


def test_a_blocked_step_is_replaced_by_what_was_proposed():
    revised = revise(plan(), blocked="check", instead=[step("ask"), step("check")])
    assert [s.name for s in revised.steps] == ["find", "ask", "check", "send"]


def test_work_already_done_is_never_rewritten():
    revised = revise(plan(), blocked="check", instead=[step("ask")])
    assert revised.steps[0].name == "find"


def test_a_step_already_done_cannot_be_the_blocked_one():
    with pytest.raises(ValueError):
        revise(plan(), blocked="find", instead=[step("ask")])


def test_a_step_not_in_the_plan_cannot_be_the_blocked_one():
    with pytest.raises(ValueError):
        revise(plan(), blocked="nowhere", instead=[step("ask")])


def test_dropping_a_blocked_step_with_nothing_in_its_place_is_allowed():
    revised = revise(plan(), blocked="check", instead=[])
    assert [s.name for s in revised.steps] == ["find", "send"]


def test_dropping_a_required_step_is_reported_as_a_narrowing():
    revised = revise(plan(), blocked="check", instead=[])
    assert revised.narrowed is True


def test_replacing_a_step_is_not_a_narrowing():
    revised = revise(plan(), blocked="check", instead=[step("ask")])
    assert revised.narrowed is False


def test_dropping_an_optional_step_is_not_a_narrowing():
    optional = [step("find", done=True), step("check", required=False), step("send")]
    assert revise(optional, blocked="check", instead=[]).narrowed is False


def test_a_revision_that_changes_nothing_after_an_effect_still_keeps_the_effect():
    acted = [step("find", done=True, had_effects=True), step("check")]
    revised = revise(acted, blocked="check", instead=[step("ask")])
    assert revised.steps[0].had_effects is True


def test_the_person_is_told_when_the_plan_changed_under_them():
    revised = revise(plan(), blocked="check", instead=[step("ask")])
    assert revised.worth_mentioning is True


def test_a_narrowed_plan_must_be_agreed_rather_than_just_mentioned():
    revised = revise(plan(), blocked="check", instead=[])
    assert revised.needs_agreement is True


def test_a_like_for_like_replacement_does_not_need_agreement():
    revised = revise(plan(), blocked="check", instead=[step("ask")])
    assert revised.needs_agreement is False


def test_a_replacement_step_cannot_claim_to_be_already_done():
    with pytest.raises(ValueError):
        revise(plan(), blocked="check", instead=[step("ask", done=True)])


def test_a_replacement_cannot_repeat_a_name_already_in_the_plan():
    with pytest.raises(ValueError):
        revise(plan(), blocked="check", instead=[step("find")])


def test_an_empty_plan_cannot_be_revised():
    with pytest.raises(ValueError):
        revise([], blocked="check", instead=[step("ask")])
