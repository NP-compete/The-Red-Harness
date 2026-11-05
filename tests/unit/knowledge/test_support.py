"""Checking that what the answer claims is actually in what was read."""

from __future__ import annotations

import pytest

from agent.src.knowledge.support import Claim, Passage, check_support

PASSAGES = (
    Passage(source="handbook", text="Expenses over 500 need a manager's approval."),
    Passage(source="policy", text="Travel is booked through the central agency."),
)


def test_a_claim_taken_from_a_passage_is_supported():
    claim = Claim(text="Expenses over 500 need approval.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).claims[0].supported is True


def test_a_claim_nothing_backs_is_unsupported():
    claim = Claim(
        text="Expenses are reimbursed within three days.", cites=("handbook",)
    )
    assert check_support([claim], passages=PASSAGES).claims[0].supported is False


def test_a_claim_citing_a_passage_that_was_not_read_is_unsupported():
    claim = Claim(text="Travel is booked centrally.", cites=("invented",))
    assert check_support([claim], passages=PASSAGES).claims[0].supported is False


def test_citing_something_that_was_not_read_is_called_out():
    claim = Claim(text="Travel is booked centrally.", cites=("invented",))
    assert "invented" in check_support([claim], passages=PASSAGES).claims[0].reason


def test_a_claim_with_no_citation_at_all_is_unsupported():
    claim = Claim(text="Expenses over 500 need approval.", cites=())
    assert check_support([claim], passages=PASSAGES).claims[0].supported is False


def test_an_uncited_claim_says_it_needs_a_source():
    claim = Claim(text="Expenses over 500 need approval.", cites=())
    assert "source" in check_support([claim], passages=PASSAGES).claims[0].reason


def test_a_claim_may_be_supported_by_any_of_the_passages_it_cites():
    claim = Claim(
        text="Travel is booked through the central agency.",
        cites=("handbook", "policy"),
    )
    assert check_support([claim], passages=PASSAGES).claims[0].supported is True


def test_the_passage_that_supports_a_claim_is_named():
    claim = Claim(
        text="Travel is booked through the central agency.",
        cites=("handbook", "policy"),
    )
    assert check_support([claim], passages=PASSAGES).claims[0].supported_by == "policy"


def test_an_answer_where_everything_is_supported_is_grounded():
    claim = Claim(text="Expenses over 500 need approval.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).grounded is True


def test_one_unsupported_claim_makes_the_answer_ungrounded():
    claims = [
        Claim(text="Expenses over 500 need approval.", cites=("handbook",)),
        Claim(text="Reimbursement takes three days.", cites=("handbook",)),
    ]
    assert check_support(claims, passages=PASSAGES).grounded is False


def test_the_share_of_supported_claims_is_reported():
    claims = [
        Claim(text="Expenses over 500 need approval.", cites=("handbook",)),
        Claim(text="Reimbursement takes three days.", cites=("handbook",)),
    ]
    assert check_support(claims, passages=PASSAGES).supported_share == 0.5


def test_the_unsupported_claims_are_listed_so_they_can_be_removed():
    claims = [
        Claim(text="Expenses over 500 need approval.", cites=("handbook",)),
        Claim(text="Reimbursement takes three days.", cites=("handbook",)),
    ]
    result = check_support(claims, passages=PASSAGES)
    assert result.unsupported == ("Reimbursement takes three days.",)


def test_an_answer_with_no_claims_is_not_called_grounded():
    assert check_support([], passages=PASSAGES).grounded is False


def test_an_answer_with_no_claims_says_there_was_nothing_to_check():
    assert "nothing" in check_support([], passages=PASSAGES).reason


def test_checking_against_no_passages_at_all_is_refused():
    claim = Claim(text="anything", cites=("handbook",))
    with pytest.raises(ValueError):
        check_support([claim], passages=())


def test_a_claim_with_no_text_is_refused():
    with pytest.raises(ValueError):
        Claim(text="   ", cites=("handbook",))


def test_a_passage_with_no_source_is_refused():
    with pytest.raises(ValueError):
        Passage(source=" ", text="something")


def test_a_claim_that_denies_what_the_passage_says_is_not_supported():
    claim = Claim(text="Expenses over 500 do not need approval.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).claims[0].supported is False


def test_a_contradiction_is_distinguished_from_a_missing_source():
    claim = Claim(text="Expenses over 500 do not need approval.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).claims[0].contradicted is True


def test_an_ordinary_unsupported_claim_is_not_a_contradiction():
    claim = Claim(text="Reimbursement takes three days.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).claims[0].contradicted is False


def test_a_contradiction_says_what_the_passage_actually_says():
    claim = Claim(text="Expenses over 500 do not need approval.", cites=("handbook",))
    assert "handbook" in check_support([claim], passages=PASSAGES).claims[0].reason


def test_a_claim_matching_a_negative_passage_is_still_supported():
    passages = (
        Passage(source="rules", text="Contractors are not eligible for the bonus."),
    )
    claim = Claim(text="Contractors are not eligible for the bonus.", cites=("rules",))
    assert check_support([claim], passages=passages).claims[0].supported is True


def test_a_claim_affirming_what_a_passage_denies_is_contradicted():
    passages = (
        Passage(source="rules", text="Contractors are not eligible for the bonus."),
    )
    claim = Claim(text="Contractors are eligible for the bonus.", cites=("rules",))
    assert check_support([claim], passages=passages).claims[0].contradicted is True


def test_contradictions_are_collected_for_the_answer_as_a_whole():
    claim = Claim(text="Expenses over 500 do not need approval.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).contradicted == (
        "Expenses over 500 do not need approval.",
    )


def test_an_answer_with_a_contradiction_is_not_grounded():
    claim = Claim(text="Expenses over 500 do not need approval.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).grounded is False


def test_a_claim_with_a_different_number_is_not_supported():
    claim = Claim(text="Expenses over 1000 need approval.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).claims[0].supported is False


def test_a_changed_number_says_the_figure_does_not_match():
    claim = Claim(text="Expenses over 1000 need approval.", cites=("handbook",))
    assert "1000" in check_support([claim], passages=PASSAGES).claims[0].reason


def test_a_claim_repeating_the_same_number_is_still_supported():
    claim = Claim(text="Expenses over 500 need approval.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).claims[0].supported is True


def test_a_claim_that_flips_the_comparison_contradicts_the_passage():
    claim = Claim(text="Expenses under 500 need approval.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).claims[0].contradicted is True


def test_a_flipped_comparison_is_not_merely_unsupported():
    claim = Claim(text="Expenses under 500 need approval.", cites=("handbook",))
    assert check_support([claim], passages=PASSAGES).claims[0].supported is False


def test_a_claim_widening_a_quantifier_contradicts_the_passage():
    passages = (
        Passage(source="rules", text="Some contractors are eligible for the bonus."),
    )
    claim = Claim(text="All contractors are eligible for the bonus.", cites=("rules",))
    assert check_support([claim], passages=passages).claims[0].contradicted is True


def test_a_claim_keeping_the_quantifier_is_supported():
    passages = (
        Passage(source="rules", text="Some contractors are eligible for the bonus."),
    )
    claim = Claim(text="Some contractors are eligible for the bonus.", cites=("rules",))
    assert check_support([claim], passages=passages).claims[0].supported is True


def test_a_claim_with_no_numbers_against_a_passage_with_some_is_unaffected():
    passages = (Passage(source="rules", text="Travel over 500 miles needs a form."),)
    claim = Claim(text="Travel needs a form.", cites=("rules",))
    assert check_support([claim], passages=passages).claims[0].supported is True
