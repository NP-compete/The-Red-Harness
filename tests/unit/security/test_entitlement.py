"""Who is allowed to use which agent, and how many of them there are."""

from __future__ import annotations

import pytest

from agent.src.security.entitlement import (
    Entitlements,
    Refusal,
    may_use,
    take_seat,
)

ENTITLEMENTS = Entitlements(
    agents_by_team={"finance": ("reporter", "reconciler"), "support": ("triage",)},
    seats_by_team={"finance": 2, "support": 1},
    seats_taken={"finance": ("ana",), "support": ("bo",)},
)


def test_a_member_may_use_an_agent_their_team_has():
    assert may_use(
        "ana", team="finance", agent="reporter", entitlements=ENTITLEMENTS
    ).permitted


def test_a_member_may_not_use_an_agent_their_team_does_not_have():
    decision = may_use("ana", team="finance", agent="triage", entitlements=ENTITLEMENTS)
    assert decision.permitted is False


def test_an_agent_the_team_lacks_is_named_in_the_refusal():
    decision = may_use("ana", team="finance", agent="triage", entitlements=ENTITLEMENTS)
    assert decision.refusal is Refusal.AGENT_NOT_LICENSED


def test_a_team_with_no_entitlements_may_use_nothing():
    decision = may_use("cy", team="legal", agent="reporter", entitlements=ENTITLEMENTS)
    assert decision.permitted is False


def test_an_unknown_team_is_told_it_has_no_licence_rather_than_no_such_agent():
    decision = may_use("cy", team="legal", agent="reporter", entitlements=ENTITLEMENTS)
    assert decision.refusal is Refusal.TEAM_NOT_LICENSED


def test_someone_already_holding_a_seat_keeps_using_it():
    assert may_use(
        "ana", team="finance", agent="reporter", entitlements=ENTITLEMENTS
    ).permitted


def test_a_new_person_takes_a_free_seat():
    result = take_seat("dee", team="finance", entitlements=ENTITLEMENTS)
    assert result.permitted is True


def test_taking_a_seat_records_the_person():
    result = take_seat("dee", team="finance", entitlements=ENTITLEMENTS)
    assert "dee" in result.entitlements.seats_taken["finance"]


def test_taking_a_seat_leaves_the_original_untouched():
    take_seat("dee", team="finance", entitlements=ENTITLEMENTS)
    assert ENTITLEMENTS.seats_taken["finance"] == ("ana",)


def test_a_full_team_cannot_seat_another_person():
    result = take_seat("cy", team="support", entitlements=ENTITLEMENTS)
    assert result.permitted is False


def test_a_full_team_is_told_the_seats_are_gone():
    result = take_seat("cy", team="support", entitlements=ENTITLEMENTS)
    assert result.refusal is Refusal.NO_SEATS_LEFT


def test_a_full_team_is_told_how_many_seats_there_are():
    result = take_seat("cy", team="support", entitlements=ENTITLEMENTS)
    assert "1" in result.reason


def test_taking_a_seat_twice_does_not_use_two_seats():
    result = take_seat("bo", team="support", entitlements=ENTITLEMENTS)
    assert result.permitted is True
    assert result.entitlements.seats_taken["support"] == ("bo",)


def test_someone_without_a_seat_cannot_use_an_agent():
    decision = may_use(
        "dee", team="finance", agent="reporter", entitlements=ENTITLEMENTS
    )
    assert decision.refusal is Refusal.NO_SEAT


def test_the_licence_is_checked_before_the_seat():
    decision = may_use("dee", team="finance", agent="triage", entitlements=ENTITLEMENTS)
    assert decision.refusal is Refusal.AGENT_NOT_LICENSED


def test_seats_counted_above_the_limit_are_refused():
    with pytest.raises(ValueError):
        Entitlements(
            agents_by_team={"finance": ("reporter",)},
            seats_by_team={"finance": 1},
            seats_taken={"finance": ("ana", "bo")},
        )


def test_a_negative_seat_count_is_refused():
    with pytest.raises(ValueError):
        Entitlements(agents_by_team={}, seats_by_team={"finance": -1}, seats_taken={})
