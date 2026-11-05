"""Turning a filed complaint into a case the suite can run."""

from __future__ import annotations

import pytest

from agent.src.evals.case_generation import Complaint, Existing, propose_case


def complaint(**kwargs) -> Complaint:
    defaults = {
        "run": "r1",
        "question": "What is the travel limit?",
        "answer_given": "750 euros",
        "what_was_wrong": "the number was wrong",
        "expected": "500 euros",
        "reproducible": True,
        "content_kept": True,
        "contains_personal_data": False,
    }
    defaults.update(kwargs)
    return Complaint(**defaults)


def existing(*questions: str) -> list[Existing]:
    return [Existing(case=f"c{i}", question=q) for i, q in enumerate(questions)]


def test_a_clear_complaint_becomes_a_case():
    assert propose_case(complaint(), existing=[]).proposed is True


def test_the_question_becomes_the_case_question():
    case = propose_case(complaint(), existing=[])
    assert case.question == "What is the travel limit?"


def test_what_the_person_expected_becomes_what_the_case_expects():
    case = propose_case(complaint(), existing=[])
    assert case.expected == "500 euros"


def test_a_complaint_with_nothing_expected_cannot_be_graded():
    vague = complaint(expected="")
    assert propose_case(vague, existing=[]).proposed is False


def test_an_ungradable_complaint_says_what_is_missing():
    vague = complaint(expected="")
    assert "expected" in propose_case(vague, existing=[]).reason


def test_a_complaint_that_cannot_be_reproduced_is_not_made_into_a_case():
    flaky = complaint(reproducible=False)
    assert propose_case(flaky, existing=[]).proposed is False


def test_a_complaint_whose_content_was_not_kept_cannot_become_a_case():
    withheld = complaint(content_kept=False)
    assert propose_case(withheld, existing=[]).proposed is False


def test_a_question_already_in_the_suite_is_not_added_twice():
    already = existing("What is the travel limit?")
    assert propose_case(complaint(), existing=already).proposed is False


def test_a_duplicate_points_at_the_case_that_already_covers_it():
    already = existing("What is the travel limit?")
    assert propose_case(complaint(), existing=already).duplicate_of == "c0"


def test_a_question_matching_but_for_wording_is_still_a_duplicate():
    already = existing("what is the TRAVEL limit?  ")
    assert propose_case(complaint(), existing=already).proposed is False


def test_a_different_question_is_not_a_duplicate():
    already = existing("What is the expense limit?")
    assert propose_case(complaint(), existing=already).proposed is True


def test_personal_data_in_a_complaint_means_the_case_is_held_for_review():
    personal = complaint(contains_personal_data=True)
    assert propose_case(personal, existing=[]).needs_review is True


def test_an_ordinary_case_needs_no_review():
    assert propose_case(complaint(), existing=[]).needs_review is False


def test_a_personal_case_is_still_proposed():
    personal = complaint(contains_personal_data=True)
    assert propose_case(personal, existing=[]).proposed is True


def test_the_run_it_came_from_is_recorded():
    assert propose_case(complaint(), existing=[]).from_run == "r1"


def test_a_complaint_with_no_question_is_refused():
    with pytest.raises(ValueError):
        complaint(question="  ")
