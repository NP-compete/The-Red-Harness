"""Approving a plan once instead of each step as it arrives."""

from __future__ import annotations

import pytest

from agent.src.security.plan_consent import PlanConsent, Step


def steps() -> list[Step]:
    return [
        Step(tool="tracker.search", writes=False),
        Step(tool="docs.list", writes=False),
        Step(tool="tracker.create_issue", writes=True),
    ]


def consent(**kwargs) -> PlanConsent:
    return PlanConsent(kwargs.pop("steps", steps()), **kwargs)


def test_a_plan_names_the_steps_that_change_something():
    assert [s.tool for s in consent().acting_steps] == ["tracker.create_issue"]


def test_an_unapproved_plan_covers_nothing():
    assert consent().use_for(Step(tool="tracker.create_issue", writes=True)) is False


def test_approval_covers_the_steps_in_the_plan():
    c = consent()
    c.approve()
    assert c.use_for(Step(tool="tracker.create_issue", writes=True)) is True


def test_approval_does_not_cover_a_step_that_was_not_shown():
    c = consent()
    c.approve()
    assert c.use_for(Step(tool="mail.send", writes=True)) is False


def test_a_step_is_covered_only_as_many_times_as_it_appeared():
    c = consent(steps=[Step(tool="tracker.create_issue", writes=True)])
    c.approve()
    step = Step(tool="tracker.create_issue", writes=True)
    assert c.use_for(step) is True
    assert c.use_for(step) is False


def test_a_repeated_step_is_covered_each_time_it_was_planned():
    c = consent(
        steps=[
            Step(tool="tracker.create_issue", writes=True),
            Step(tool="tracker.create_issue", writes=True),
        ]
    )
    c.approve()
    step = Step(tool="tracker.create_issue", writes=True)
    assert [c.use_for(step), c.use_for(step), c.use_for(step)] == [True, True, False]


def test_a_read_step_needs_no_cover_and_does_not_consume_one():
    c = consent()
    c.approve()
    c.use_for(Step(tool="tracker.search", writes=False))
    assert c.use_for(Step(tool="tracker.create_issue", writes=True)) is True


def test_a_plan_can_be_approved_read_only():
    c = consent()
    c.approve(acting=False)
    assert c.use_for(Step(tool="tracker.create_issue", writes=True)) is False


def test_revoking_withdraws_what_is_left():
    c = consent()
    c.approve()
    c.revoke()
    assert c.use_for(Step(tool="tracker.create_issue", writes=True)) is False


def test_approving_twice_does_not_double_the_allowance():
    c = consent(steps=[Step(tool="tracker.create_issue", writes=True)])
    c.approve()
    c.approve()
    step = Step(tool="tracker.create_issue", writes=True)
    assert [c.use_for(step), c.use_for(step)] == [True, False]


def test_an_empty_plan_is_refused():
    with pytest.raises(ValueError):
        PlanConsent([])
