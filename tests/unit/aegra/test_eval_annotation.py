"""Which graded turns of an eval run a person should look at."""

from __future__ import annotations

from agent.aegra.eval_annotation import queue_from_turns


def turn(**kwargs) -> dict:
    defaults = {
        "turn_id": "q1",
        "metric_identifier": "accuracy",
        "result": "PASS",
        "score": "0.90",
        "threshold": "0.50",
    }
    defaults.update(kwargs)
    return defaults


def test_a_comfortable_pass_needs_no_one():
    assert queue_from_turns([turn()]) == []


def test_a_failed_turn_goes_to_a_person():
    failed = turn(result="FAIL", score="0.20")
    assert [entry["item"] for entry in queue_from_turns([failed])] == ["q1"]


def test_a_failure_is_named_as_the_reason():
    failed = turn(result="FAIL", score="0.20")
    assert queue_from_turns([failed])[0]["reason"] == "failed"


def test_a_score_sitting_on_its_threshold_is_not_a_confident_grade():
    borderline = turn(score="0.52", threshold="0.50")
    assert queue_from_turns([borderline])[0]["reason"] == "low_confidence"


def test_a_score_well_clear_of_its_threshold_is_confident():
    assert queue_from_turns([turn(score="0.90", threshold="0.50")]) == []


def test_two_graders_disagreeing_about_one_turn_goes_to_a_person():
    turns = [
        turn(metric_identifier="accuracy", result="PASS"),
        turn(metric_identifier="helpfulness", result="FAIL", score="0.20"),
    ]
    assert queue_from_turns(turns)[0]["reason"] == "disagreement"


def test_a_turn_two_graders_agree_on_is_left_alone():
    turns = [
        turn(metric_identifier="accuracy", result="PASS"),
        turn(metric_identifier="helpfulness", result="PASS"),
    ]
    assert queue_from_turns(turns) == []


def test_disagreement_outranks_the_failing_half_of_it():
    turns = [
        turn(metric_identifier="accuracy", result="PASS"),
        turn(metric_identifier="helpfulness", result="FAIL", score="0.20"),
    ]
    assert [entry["reason"] for entry in queue_from_turns(turns)] == ["disagreement"]


def test_a_turn_is_queued_once_however_many_metrics_graded_it():
    turns = [
        turn(metric_identifier="accuracy", result="FAIL", score="0.20"),
        turn(metric_identifier="helpfulness", result="FAIL", score="0.10"),
    ]
    assert len(queue_from_turns(turns)) == 1


def test_a_turn_that_errored_goes_to_a_person():
    assert queue_from_turns([turn(result="ERROR", score="")])[0]["reason"] == "failed"


def test_a_turn_with_no_score_at_all_is_not_guessed_about():
    assert queue_from_turns([turn(result="PASS", score="", threshold="")]) == []


def test_an_unreadable_score_is_not_guessed_about():
    assert queue_from_turns([turn(score="n/a", threshold="0.50")]) == []


def test_the_most_useful_turn_to_look_at_comes_first():
    turns = [
        turn(turn_id="q1", score="0.52"),
        turn(turn_id="q2", metric_identifier="accuracy", result="PASS"),
        turn(turn_id="q2", metric_identifier="helpfulness", result="FAIL", score="0.1"),
    ]
    assert [entry["item"] for entry in queue_from_turns(turns)] == ["q2", "q1"]


def test_a_run_with_no_turns_asks_for_nothing():
    assert queue_from_turns([]) == []
