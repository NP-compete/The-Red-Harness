"""Keeping one tool result from swallowing the whole conversation."""

from __future__ import annotations

import pytest

from agent.src.security.tool_result_limits import trim


def test_a_small_result_passes_through():
    assert trim("short answer", max_chars=100).text == "short answer"


def test_a_small_result_is_not_marked_as_trimmed():
    assert trim("short", max_chars=100).trimmed is False


def test_a_long_result_is_cut():
    assert len(trim("x" * 500, max_chars=100).text) <= 100


def test_a_cut_result_says_so():
    assert trim("x" * 500, max_chars=100).trimmed is True


def test_the_agent_is_told_how_much_was_left_out():
    result = trim("x" * 500, max_chars=100)
    assert "400" in result.note


def test_the_beginning_is_kept_because_that_is_where_the_answer_usually_is():
    assert trim("important start" + "x" * 500, max_chars=50).text.startswith(
        "important start"
    )


def test_the_end_can_be_kept_instead():
    result = trim("x" * 500 + "important end", max_chars=50, keep="end")
    assert result.text.endswith("important end")


def test_both_ends_can_be_kept():
    result = trim("start" + "x" * 500 + "finish", max_chars=60, keep="both")
    assert result.text.startswith("start") and result.text.endswith("finish")


def test_the_middle_is_marked_when_both_ends_are_kept():
    result = trim("start" + "x" * 500 + "finish", max_chars=60, keep="both")
    assert "…" in result.text


def test_an_empty_result_is_left_alone():
    assert trim("", max_chars=100).text == ""


def test_the_original_length_is_reported_for_the_record():
    assert trim("x" * 500, max_chars=100).original_chars == 500


@pytest.mark.parametrize("limit", [0, -1])
def test_a_nonsense_limit_is_refused(limit):
    with pytest.raises(ValueError):
        trim("anything", max_chars=limit)
