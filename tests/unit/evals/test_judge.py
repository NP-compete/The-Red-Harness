"""Scoring an answer against a rubric, and knowing when not to trust the score."""

from __future__ import annotations

import pytest

from agent.src.evals.judge import Criterion, Judgement, Rubric, score_answer

RUBRIC = Rubric(
    criteria=(
        Criterion(name="answers the question", weight=2.0, required=True),
        Criterion(name="cites its sources", weight=1.0, required=False),
        Criterion(name="stays on topic", weight=1.0, required=False),
    ),
    pass_mark=0.7,
)


def test_meeting_everything_passes():
    met = {
        "answers the question": True,
        "cites its sources": True,
        "stays on topic": True,
    }
    assert score_answer(met, rubric=RUBRIC).passed is True


def test_meeting_everything_scores_full_marks():
    met = {
        "answers the question": True,
        "cites its sources": True,
        "stays on topic": True,
    }
    assert score_answer(met, rubric=RUBRIC).score == 1.0


def test_weight_decides_how_much_each_criterion_counts():
    partial = {
        "answers the question": True,
        "cites its sources": False,
        "stays on topic": False,
    }
    assert score_answer(partial, rubric=RUBRIC).score == 0.5


def test_missing_a_required_criterion_fails_whatever_the_score():
    partial = {
        "answers the question": False,
        "cites its sources": True,
        "stays on topic": True,
    }
    assert score_answer(partial, rubric=RUBRIC).passed is False


def test_a_failed_requirement_is_named():
    partial = {
        "answers the question": False,
        "cites its sources": True,
        "stays on topic": True,
    }
    assert "answers the question" in score_answer(partial, rubric=RUBRIC).reason


def test_scoring_below_the_pass_mark_fails():
    partial = {
        "answers the question": True,
        "cites its sources": False,
        "stays on topic": False,
    }
    assert score_answer(partial, rubric=RUBRIC).passed is False


def test_scoring_exactly_the_pass_mark_passes():
    rubric = Rubric(
        criteria=(Criterion(name="a", weight=1.0, required=False),), pass_mark=1.0
    )
    assert score_answer({"a": True}, rubric=rubric).passed is True


def test_a_criterion_the_judge_did_not_answer_counts_against_it():
    assert score_answer({"answers the question": True}, rubric=RUBRIC).score == 0.5


def test_an_unanswered_criterion_is_reported_rather_than_assumed():
    result = score_answer({"answers the question": True}, rubric=RUBRIC)
    assert set(result.unanswered) == {"cites its sources", "stays on topic"}


def test_too_many_unanswered_criteria_makes_the_judgement_unreliable():
    assert score_answer({}, rubric=RUBRIC).reliable is False


def test_a_complete_judgement_is_reliable():
    met = {
        "answers the question": True,
        "cites its sources": True,
        "stays on topic": True,
    }
    assert score_answer(met, rubric=RUBRIC).reliable is True


def test_an_unreliable_judgement_does_not_claim_a_pass():
    assert score_answer({}, rubric=RUBRIC).passed is False


def test_a_criterion_not_in_the_rubric_is_refused():
    with pytest.raises(ValueError):
        score_answer({"invented": True}, rubric=RUBRIC)


def test_a_rubric_with_no_criteria_is_refused():
    with pytest.raises(ValueError):
        Rubric(criteria=(), pass_mark=0.5)


def test_a_criterion_with_no_weight_is_refused():
    with pytest.raises(ValueError):
        Criterion(name="a", weight=0.0, required=False)


@pytest.mark.parametrize("mark", [-0.1, 1.1])
def test_an_impossible_pass_mark_is_refused(mark):
    with pytest.raises(ValueError):
        Rubric(
            criteria=(Criterion(name="a", weight=1.0, required=False),), pass_mark=mark
        )


def test_a_judgement_is_a_record_of_what_was_checked():
    met = {
        "answers the question": True,
        "cites its sources": False,
        "stays on topic": True,
    }
    result = score_answer(met, rubric=RUBRIC)
    assert isinstance(result, Judgement) and result.met == (
        "answers the question",
        "stays on topic",
    )
