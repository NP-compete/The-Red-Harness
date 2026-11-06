"""Deciding whether to ask rather than guess."""

from __future__ import annotations

import pytest

from agent.src.agent.clarification import Ambiguity, Request, should_ask


def request(**kwargs) -> Request:
    defaults = {
        "ambiguities": (),
        "reversible": True,
        "unattended": False,
        "attempts_so_far": 0,
    }
    defaults.update(kwargs)
    return Request(**defaults)


def test_a_clear_request_is_acted_on():
    assert should_ask(request()).ask is False


def test_an_ambiguous_request_is_queried():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.5
    )
    assert should_ask(request(ambiguities=(ambiguity,))).ask is True


def test_the_question_names_what_is_unclear():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.5
    )
    assert "which report" in should_ask(request(ambiguities=(ambiguity,))).question


def test_the_question_offers_the_possibilities():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.5
    )
    assert should_ask(request(ambiguities=(ambiguity,))).options == (
        "weekly",
        "monthly",
    )


def test_a_likely_reading_is_acted_on_without_asking():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.95
    )
    assert should_ask(request(ambiguities=(ambiguity,))).ask is False


def test_the_assumed_reading_is_stated_when_not_asking():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.95
    )
    assert should_ask(request(ambiguities=(ambiguity,))).assuming == "weekly"


def test_a_clear_request_assumes_nothing():
    assert should_ask(request()).assuming == ""


def test_an_irreversible_action_is_queried_even_when_likely():
    ambiguity = Ambiguity(
        about="which account", options=("savings", "current"), confidence=0.95
    )
    assert should_ask(request(ambiguities=(ambiguity,), reversible=False)).ask is True


def test_an_unattended_run_cannot_ask():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.5
    )
    assert should_ask(request(ambiguities=(ambiguity,), unattended=True)).ask is False


def test_an_unattended_run_that_cannot_ask_stops_instead_of_guessing():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.5
    )
    decision = should_ask(request(ambiguities=(ambiguity,), unattended=True))
    assert decision.stop is True


def test_an_unattended_run_says_why_it_stopped():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.5
    )
    decision = should_ask(request(ambiguities=(ambiguity,), unattended=True))
    assert "nobody" in decision.reason


def test_an_unattended_run_proceeds_when_the_reading_is_clear_enough():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.95
    )
    decision = should_ask(request(ambiguities=(ambiguity,), unattended=True))
    assert decision.stop is False and decision.ask is False


def test_asking_the_same_thing_repeatedly_is_avoided():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.5
    )
    decision = should_ask(request(ambiguities=(ambiguity,), attempts_so_far=2))
    assert decision.ask is False


def test_giving_up_on_asking_states_the_assumption_instead():
    ambiguity = Ambiguity(
        about="which report", options=("weekly", "monthly"), confidence=0.5
    )
    decision = should_ask(request(ambiguities=(ambiguity,), attempts_so_far=2))
    assert decision.assuming == "weekly"


def test_the_most_uncertain_thing_is_asked_about_first():
    unclear = Ambiguity(about="which report", options=("a", "b"), confidence=0.4)
    clearer = Ambiguity(about="which month", options=("may", "june"), confidence=0.8)
    assert (
        "which report" in should_ask(request(ambiguities=(clearer, unclear))).question
    )


def test_only_one_question_is_asked_at_a_time():
    first = Ambiguity(about="which report", options=("a", "b"), confidence=0.4)
    second = Ambiguity(about="which month", options=("may", "june"), confidence=0.45)
    assert should_ask(request(ambiguities=(first, second))).question.count("?") == 1


def test_an_ambiguity_with_one_option_is_refused():
    with pytest.raises(ValueError):
        Ambiguity(about="which report", options=("weekly",), confidence=0.5)


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_an_impossible_confidence_is_refused(confidence):
    with pytest.raises(ValueError):
        Ambiguity(about="x", options=("a", "b"), confidence=confidence)
