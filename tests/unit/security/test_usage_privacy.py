"""Reporting how much the agent is used, without reporting on people."""

from __future__ import annotations

import pytest

from agent.src.security.usage_privacy import Event, summarise

EVENTS = [
    Event(subject="a@example.com", team="sre", tokens=100, approvals=1, refusals=0),
    Event(subject="a@example.com", team="sre", tokens=200, approvals=0, refusals=1),
    Event(subject="b@example.com", team="sre", tokens=300, approvals=2, refusals=0),
    Event(subject="c@example.com", team="finance", tokens=400, approvals=0, refusals=0),
]


def report(**kwargs):
    kwargs.setdefault("per_person", False)
    return summarise(EVENTS, **kwargs)


def test_totals_are_reported():
    assert report().totals["tokens"] == 1000


def test_approvals_and_refusals_are_counted():
    assert report().totals["approvals"] == 3
    assert report().totals["refusals"] == 1


def test_nobody_is_named_by_default():
    assert report().per_person == {}


def test_team_figures_are_available_without_naming_anybody():
    assert report().per_team["sre"]["tokens"] == 600


def test_a_team_of_one_is_not_reported_as_a_team():
    assert "finance" not in report().per_team


def test_a_small_team_can_be_reported_when_the_floor_is_lowered():
    assert "finance" in summarise(EVENTS, per_person=False, min_team_size=1).per_team


def test_per_person_figures_appear_only_when_asked_for():
    assert (
        summarise(EVENTS, per_person=True).per_person["a@example.com"]["tokens"] == 300
    )


def test_turning_on_per_person_is_recorded_in_the_report():
    assert summarise(EVENTS, per_person=True).discloses_individuals is True


def test_an_aggregate_report_says_it_names_nobody():
    assert report().discloses_individuals is False


def test_an_empty_period_reports_zero_rather_than_nothing():
    empty = summarise([], per_person=False)
    assert empty.totals["tokens"] == 0


def test_no_message_content_can_reach_the_report():
    assert not any(
        hasattr(EVENTS[0], field) for field in ("text", "prompt", "messages")
    )


@pytest.mark.parametrize("floor", [0, -1])
def test_a_nonsense_team_floor_is_refused(floor):
    with pytest.raises(ValueError):
        summarise(EVENTS, per_person=False, min_team_size=floor)
