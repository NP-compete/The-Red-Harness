"""Choosing which graded items a person should look at."""

from __future__ import annotations

import pytest

from agent.src.evals.annotation import Graded, Reason, build_queue


def graded(**kwargs) -> Graded:
    defaults = {
        "item": "q1",
        "score": 0.9,
        "confidence": 0.9,
        "graders_disagreed": False,
        "already_reviewed": False,
        "flagged_by_person": False,
    }
    defaults.update(kwargs)
    return Graded(**defaults)


def test_a_confident_agreed_pass_needs_no_one():
    assert build_queue([graded()]) == []


def test_graders_that_disagreed_go_to_a_person():
    split = graded(graders_disagreed=True)
    assert [entry.item for entry in build_queue([split])] == ["q1"]


def test_disagreement_is_named_as_the_reason():
    split = graded(graders_disagreed=True)
    assert build_queue([split])[0].reason is Reason.DISAGREEMENT


def test_a_grade_given_with_little_confidence_goes_to_a_person():
    unsure = graded(confidence=0.2)
    assert build_queue([unsure])[0].reason is Reason.LOW_CONFIDENCE


def test_a_failure_is_worth_a_person_s_eye_even_when_confident():
    failed = graded(score=0.1)
    assert build_queue([failed])[0].reason is Reason.FAILED


def test_something_a_person_flagged_is_always_queued():
    flagged = graded(flagged_by_person=True)
    assert build_queue([flagged])[0].reason is Reason.FLAGGED


def test_something_already_reviewed_is_not_asked_about_again():
    seen = graded(graders_disagreed=True, already_reviewed=True)
    assert build_queue([seen]) == []


def test_a_flag_outranks_having_been_reviewed():
    flagged = graded(already_reviewed=True, flagged_by_person=True)
    assert [entry.item for entry in build_queue([flagged])] == ["q1"]


def test_a_flag_is_the_first_reason_given():
    flagged = graded(flagged_by_person=True, graders_disagreed=True, score=0.1)
    assert build_queue([flagged])[0].reason is Reason.FLAGGED


def test_disagreement_outranks_a_low_score():
    both = graded(graders_disagreed=True, score=0.1)
    assert build_queue([both])[0].reason is Reason.DISAGREEMENT


def test_the_most_useful_item_to_look_at_comes_first():
    ordinary = graded(item="q1", confidence=0.2)
    flagged = graded(item="q2", flagged_by_person=True)
    assert [entry.item for entry in build_queue([ordinary, flagged])] == ["q2", "q1"]


def test_an_empty_run_asks_for_nothing():
    assert build_queue([]) == []


def test_a_score_outside_its_range_is_refused():
    with pytest.raises(ValueError):
        graded(score=1.4)


def test_a_confidence_outside_its_range_is_refused():
    with pytest.raises(ValueError):
        graded(confidence=-0.1)
