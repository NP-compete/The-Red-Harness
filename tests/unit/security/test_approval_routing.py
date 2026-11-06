"""Working out who to ask about a risky step, and what happens if nobody answers."""

from __future__ import annotations

from datetime import timedelta

import pytest

from agent.src.security.approval_routing import (
    Action,
    OnTimeout,
    Route,
    route_approval,
)


def action(**kwargs) -> Action:
    defaults = {
        "tool": "deploy",
        "target": "production",
        "reversible": False,
        "cost": 0.0,
        "requested_by": "ana",
        "unattended": False,
    }
    defaults.update(kwargs)
    return Action(**defaults)


ROUTES = (
    Route(
        matches="deploy",
        approvers=("bo", "cy"),
        wait=timedelta(minutes=15),
        escalate_to="on-call",
    ),
    Route(
        matches="*", approvers=("team-lead",), wait=timedelta(hours=1), escalate_to=""
    ),
)


def test_a_matching_route_decides_who_to_ask():
    assert route_approval(action(), routes=ROUTES).approvers == ("bo", "cy")


def test_the_most_specific_route_wins():
    assert route_approval(action(tool="search"), routes=ROUTES).approvers == (
        "team-lead",
    )


def test_the_wait_comes_from_the_route():
    assert route_approval(action(), routes=ROUTES).wait == timedelta(minutes=15)


def test_the_requester_is_never_among_the_approvers():
    routes = (
        Route(
            matches="deploy",
            approvers=("ana", "bo"),
            wait=timedelta(minutes=5),
            escalate_to="",
        ),
    )
    assert route_approval(action(requested_by="ana"), routes=routes).approvers == (
        "bo",
    )


def test_a_route_leaving_nobody_to_ask_is_reported():
    routes = (
        Route(
            matches="deploy",
            approvers=("ana",),
            wait=timedelta(minutes=5),
            escalate_to="",
        ),
    )
    assert (
        route_approval(action(requested_by="ana"), routes=routes).nobody_to_ask is True
    )


def test_nobody_to_ask_means_the_action_does_not_proceed():
    routes = (
        Route(
            matches="deploy",
            approvers=("ana",),
            wait=timedelta(minutes=5),
            escalate_to="",
        ),
    )
    assert (
        route_approval(action(requested_by="ana"), routes=routes).on_timeout
        is OnTimeout.REFUSE
    )


def test_an_irreversible_action_is_refused_when_nobody_answers():
    assert (
        route_approval(action(reversible=False), routes=ROUTES).on_timeout
        is OnTimeout.REFUSE
    )


def test_a_reversible_cheap_action_may_proceed_when_nobody_answers():
    cheap = action(tool="search", reversible=True, cost=0.0)
    assert route_approval(cheap, routes=ROUTES).on_timeout is OnTimeout.PROCEED


def test_a_reversible_but_expensive_action_is_refused_when_nobody_answers():
    costly = action(tool="search", reversible=True, cost=50.0)
    assert route_approval(costly, routes=ROUTES).on_timeout is OnTimeout.REFUSE


def test_an_escalation_is_used_when_the_route_has_one():
    assert route_approval(action(), routes=ROUTES).escalate_to == "on-call"


def test_a_route_with_no_escalation_has_nobody_to_escalate_to():
    assert route_approval(action(tool="search"), routes=ROUTES).escalate_to == ""


def test_an_unattended_run_is_not_asked_to_wait_for_an_answer():
    assert route_approval(action(unattended=True), routes=ROUTES).ask_now is False


def test_an_unattended_run_still_records_who_should_be_told():
    assert route_approval(action(unattended=True), routes=ROUTES).approvers == (
        "bo",
        "cy",
    )


def test_an_attended_run_asks_at_once():
    assert route_approval(action(), routes=ROUTES).ask_now is True


def test_the_reason_explains_what_is_being_approved():
    decision = route_approval(action(), routes=ROUTES)
    assert "deploy" in decision.reason and "production" in decision.reason


def test_an_action_matching_no_route_at_all_is_refused():
    with pytest.raises(ValueError):
        route_approval(
            action(),
            routes=(
                Route(
                    matches="other",
                    approvers=("x",),
                    wait=timedelta(minutes=1),
                    escalate_to="",
                ),
            ),
        )


def test_a_route_with_no_approvers_is_refused():
    with pytest.raises(ValueError):
        Route(matches="deploy", approvers=(), wait=timedelta(minutes=5), escalate_to="")


def test_a_route_with_no_wait_is_refused():
    with pytest.raises(ValueError):
        Route(matches="deploy", approvers=("bo",), wait=timedelta(0), escalate_to="")
