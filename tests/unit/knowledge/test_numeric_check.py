"""Checking the figures in an answer against the figures that were read."""

from __future__ import annotations

import pytest

from agent.src.knowledge.numeric_check import check_numbers


def test_a_figure_that_appears_in_the_source_is_supported():
    result = check_numbers("The limit is 500 euros.", read=["The limit is 500 euros."])
    assert result.unsupported == []


def test_a_figure_that_appears_nowhere_is_unsupported():
    result = check_numbers("The limit is 750 euros.", read=["The limit is 500 euros."])
    assert result.unsupported == ["750"]


def test_several_unsupported_figures_are_all_reported():
    result = check_numbers("Between 750 and 900.", read=["The limit is 500."])
    assert result.unsupported == ["750", "900"]


def test_a_figure_from_any_of_the_sources_counts():
    result = check_numbers("The limit is 500.", read=["Nothing here.", "It is 500."])
    assert result.unsupported == []


def test_thousands_separators_do_not_make_a_figure_look_new():
    result = check_numbers("The cap is 1,500.", read=["The cap is 1500."])
    assert result.unsupported == []


def test_trailing_zeros_after_a_point_do_not_make_a_figure_look_new():
    result = check_numbers("It costs 12.50.", read=["It costs 12.5."])
    assert result.unsupported == []


def test_a_rounded_figure_is_not_treated_as_the_same_figure():
    result = check_numbers("About 13.", read=["It costs 12.5."])
    assert result.unsupported == ["13"]


def test_a_year_is_checked_like_any_other_figure():
    result = check_numbers("Agreed in 2019.", read=["Agreed in 2018."])
    assert result.unsupported == ["2019"]


def test_a_percentage_is_matched_on_its_number():
    result = check_numbers("Up 12%.", read=["Growth was 12 percent."])
    assert result.unsupported == []


def test_an_answer_with_no_figures_has_nothing_to_check():
    result = check_numbers("The limit is generous.", read=["The limit is 500."])
    assert result.checked == 0


def test_how_many_figures_were_checked_is_reported():
    result = check_numbers("Between 500 and 900.", read=["The limit is 500."])
    assert result.checked == 2


def test_an_answer_whose_figures_all_hold_up_is_trustworthy():
    result = check_numbers("The limit is 500.", read=["The limit is 500."])
    assert result.trustworthy is True


def test_an_answer_with_an_invented_figure_is_not_trustworthy():
    result = check_numbers("The limit is 750.", read=["The limit is 500."])
    assert result.trustworthy is False


def test_an_answer_with_no_figures_at_all_is_trustworthy():
    result = check_numbers("The limit is generous.", read=["The limit is 500."])
    assert result.trustworthy is True


def test_an_answer_checked_against_nothing_is_refused():
    with pytest.raises(ValueError):
        check_numbers("The limit is 500.", read=[])
