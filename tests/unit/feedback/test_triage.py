"""Turning a rating into something that can be acted on."""

from __future__ import annotations

import pytest

from agent.src.feedback.triage import Action, Rating, triage


def rating(**kwargs) -> Rating:
    defaults = {
        "run": "r1",
        "liked": False,
        "comment": "",
        "answer_had_sources": True,
        "answer_was_refused": False,
        "run_failed": False,
        "may_keep_content": True,
    }
    defaults.update(kwargs)
    return Rating(**defaults)


def test_a_rating_up_is_thanked_and_left_at_that():
    assert triage(rating(liked=True)).action is Action.THANK


def test_a_rating_down_with_no_comment_asks_what_went_wrong():
    assert triage(rating()).action is Action.ASK_WHY


def test_a_rating_down_with_a_comment_is_filed():
    told = rating(comment="the number was wrong")
    assert triage(told).action is Action.FILE


def test_a_filed_rating_keeps_what_was_said():
    told = rating(comment="the number was wrong")
    assert triage(told).comment == "the number was wrong"


def test_a_rating_down_on_a_failed_run_goes_straight_to_the_failure():
    broken = rating(run_failed=True)
    assert triage(broken).action is Action.FILE


def test_a_failure_is_filed_without_asking_for_a_reason():
    broken = rating(run_failed=True)
    assert triage(broken).asked_for_detail is False


def test_asking_why_is_recorded_as_asking():
    assert triage(rating()).asked_for_detail is True


def test_an_answer_without_sources_that_was_rated_down_is_worth_an_eval_case():
    unsourced = rating(comment="wrong", answer_had_sources=False)
    assert triage(unsourced).becomes_eval_case is True


def test_a_wrong_answer_that_did_cite_sources_is_also_worth_a_case():
    told = rating(comment="the number was wrong")
    assert triage(told).becomes_eval_case is True


def test_a_rating_up_does_not_become_an_eval_case():
    assert triage(rating(liked=True)).becomes_eval_case is False


def test_a_refusal_rated_down_is_routed_to_the_people_who_set_the_rules():
    refused = rating(comment="this should have been allowed", answer_was_refused=True)
    assert triage(refused).action is Action.ROUTE_TO_POLICY


def test_a_refusal_rated_up_is_just_thanked():
    assert triage(rating(liked=True, answer_was_refused=True)).action is Action.THANK


def test_content_is_attached_when_it_may_be_kept():
    told = rating(comment="wrong")
    assert triage(told).attach_content is True


def test_content_is_not_attached_when_it_may_not_be_kept():
    told = rating(comment="wrong", may_keep_content=False)
    assert triage(told).attach_content is False


def test_a_case_without_its_content_is_not_made():
    told = rating(comment="wrong", may_keep_content=False)
    assert triage(told).becomes_eval_case is False


def test_the_run_is_always_identified():
    assert triage(rating()).run == "r1"


def test_a_rating_with_no_run_is_refused():
    with pytest.raises(ValueError):
        rating(run="  ")
