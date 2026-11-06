"""Describing what changed between two sets of settings."""

from __future__ import annotations

import pytest

from agent.src.agent.config_diff import Change, diff_config

BEFORE = {"model": "fast", "budget": "100", "approver": "bo"}


def test_identical_settings_have_no_changes():
    assert diff_config(BEFORE, BEFORE).changes == ()


def test_identical_settings_say_nothing_changed():
    assert diff_config(BEFORE, BEFORE).summary == "nothing changed"


def test_a_changed_value_is_reported():
    after = {**BEFORE, "model": "careful"}
    assert diff_config(BEFORE, after).changes[0].kind is Change.CHANGED


def test_a_changed_value_shows_both_sides():
    after = {**BEFORE, "model": "careful"}
    change = diff_config(BEFORE, after).changes[0]
    assert (change.before, change.after) == ("fast", "careful")


def test_an_added_setting_is_reported():
    after = {**BEFORE, "region": "eu-west"}
    assert diff_config(BEFORE, after).changes[0].kind is Change.ADDED


def test_an_added_setting_has_nothing_before_it():
    after = {**BEFORE, "region": "eu-west"}
    assert diff_config(BEFORE, after).changes[0].before == ""


def test_a_removed_setting_is_reported():
    after = {key: value for key, value in BEFORE.items() if key != "approver"}
    assert diff_config(BEFORE, after).changes[0].kind is Change.REMOVED


def test_changes_are_listed_in_a_stable_order():
    after = {"model": "careful", "budget": "250", "approver": "bo"}
    assert [change.key for change in diff_config(BEFORE, after).changes] == [
        "budget",
        "model",
    ]


def test_the_number_of_changes_is_reported():
    after = {"model": "careful", "budget": "250", "approver": "bo"}
    assert diff_config(BEFORE, after).count == 2


def test_the_summary_reads_plainly():
    after = {"model": "careful", "region": "eu-west"}
    assert diff_config(BEFORE, after).summary == "1 changed, 1 added, 2 removed"


def test_a_change_that_loosens_a_limit_is_flagged():
    after = {**BEFORE, "budget": "1000"}
    assert diff_config(BEFORE, after).changes[0].loosens is True


def test_a_change_that_tightens_a_limit_is_not_flagged():
    after = {**BEFORE, "budget": "50"}
    assert diff_config(BEFORE, after).changes[0].loosens is False


def test_removing_a_setting_is_treated_as_loosening():
    after = {key: value for key, value in BEFORE.items() if key != "approver"}
    assert diff_config(BEFORE, after).changes[0].loosens is True


def test_a_change_between_words_is_not_judged_as_loosening():
    after = {**BEFORE, "model": "careful"}
    assert diff_config(BEFORE, after).changes[0].loosens is False


def test_whether_anything_loosens_is_reported_for_the_whole_diff():
    after = {**BEFORE, "budget": "1000"}
    assert diff_config(BEFORE, after).loosens is True


def test_a_tightening_diff_does_not_loosen():
    after = {**BEFORE, "budget": "50"}
    assert diff_config(BEFORE, after).loosens is False


def test_comparing_nothing_with_nothing_is_refused():
    with pytest.raises(ValueError):
        diff_config({}, {})
