"""Checking the answer is the shape that was asked for."""

from __future__ import annotations

import pytest

from agent.src.agent.output_contract import Contract, Field, check_output

CONTRACT = Contract(
    fields=(
        Field(name="summary", kind="text", required=True, max_words=50),
        Field(name="risks", kind="list", required=True, max_words=None),
        Field(name="owner", kind="text", required=False, max_words=None),
    ),
)


def test_an_answer_with_everything_asked_for_fits():
    answer = {"summary": "all good", "risks": ["none"]}
    assert check_output(answer, contract=CONTRACT).fits is True


def test_a_missing_required_field_does_not_fit():
    assert check_output({"risks": []}, contract=CONTRACT).fits is False


def test_the_missing_field_is_named():
    assert check_output({"risks": []}, contract=CONTRACT).missing == ("summary",)


def test_an_optional_field_may_be_left_out():
    answer = {"summary": "all good", "risks": ["none"]}
    assert check_output(answer, contract=CONTRACT).missing == ()


def test_a_field_of_the_wrong_shape_is_caught():
    answer = {"summary": "all good", "risks": "none"}
    assert check_output(answer, contract=CONTRACT).wrong_shape == ("risks",)


def test_a_list_where_text_belongs_is_caught():
    answer = {"summary": ["all", "good"], "risks": []}
    assert check_output(answer, contract=CONTRACT).wrong_shape == ("summary",)


def test_a_field_over_its_length_is_caught():
    answer = {"summary": " ".join(["word"] * 60), "risks": []}
    assert check_output(answer, contract=CONTRACT).too_long == ("summary",)


def test_a_field_within_its_length_is_fine():
    answer = {"summary": "short enough", "risks": []}
    assert check_output(answer, contract=CONTRACT).too_long == ()


def test_a_field_with_no_limit_is_never_too_long():
    answer = {"summary": "fine", "risks": [" ".join(["word"] * 500)]}
    assert check_output(answer, contract=CONTRACT).too_long == ()


def test_anything_extra_is_reported_rather_than_ignored():
    answer = {"summary": "fine", "risks": [], "invented": "surprise"}
    assert check_output(answer, contract=CONTRACT).unexpected == ("invented",)


def test_something_extra_does_not_by_itself_break_the_shape():
    answer = {"summary": "fine", "risks": [], "invented": "surprise"}
    assert check_output(answer, contract=CONTRACT).fits is True


def test_an_empty_required_field_counts_as_missing():
    answer = {"summary": "   ", "risks": ["none"]}
    assert check_output(answer, contract=CONTRACT).missing == ("summary",)


def test_an_empty_required_list_counts_as_present():
    answer = {"summary": "fine", "risks": []}
    assert check_output(answer, contract=CONTRACT).missing == ()


def test_several_problems_are_all_reported():
    answer = {"risks": "none"}
    result = check_output(answer, contract=CONTRACT)
    assert result.missing == ("summary",) and result.wrong_shape == ("risks",)


def test_the_summary_of_problems_reads_plainly():
    assert check_output({"risks": "none"}, contract=CONTRACT).detail == (
        "missing: summary; wrong shape: risks"
    )


def test_an_answer_that_fits_has_nothing_to_say():
    answer = {"summary": "fine", "risks": []}
    assert check_output(answer, contract=CONTRACT).detail == ""


def test_a_contract_with_no_fields_is_refused():
    with pytest.raises(ValueError):
        Contract(fields=())


def test_a_field_with_an_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        Field(name="x", kind="colour", required=True, max_words=None)


def test_a_field_with_a_length_of_nothing_is_refused():
    with pytest.raises(ValueError):
        Field(name="x", kind="text", required=True, max_words=0)
