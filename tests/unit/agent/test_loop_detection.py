"""Noticing when a run is going round in circles."""

from __future__ import annotations

import pytest

from agent.src.agent.loop_detection import Call, Pattern, inspect_calls


def call(tool: str, args: str = "{}", result: str = "ok") -> Call:
    return Call(tool=tool, arguments=args, result=result)


def test_varied_work_is_making_progress():
    calls = [call("search", '{"q":"a"}'), call("fetch", '{"url":"x"}'), call("write")]
    assert inspect_calls(calls).pattern is Pattern.PROGRESSING


def test_the_same_call_repeated_is_a_loop():
    calls = [call("search", '{"q":"a"}')] * 3
    assert inspect_calls(calls).pattern is Pattern.REPEATING


def test_two_identical_calls_are_not_yet_a_loop():
    calls = [call("search", '{"q":"a"}')] * 2
    assert inspect_calls(calls).pattern is Pattern.PROGRESSING


def test_the_repeated_call_is_named():
    calls = [call("search", '{"q":"a"}')] * 3
    assert inspect_calls(calls).repeated == "search"


def test_the_same_tool_with_different_arguments_is_not_a_loop():
    calls = [call("search", f'{{"q":"{n}"}}') for n in range(5)]
    assert inspect_calls(calls).pattern is Pattern.PROGRESSING


def test_alternating_between_two_calls_is_a_loop():
    calls = [call("a"), call("b"), call("a"), call("b"), call("a"), call("b")]
    assert inspect_calls(calls).pattern is Pattern.ALTERNATING


def test_a_short_alternation_is_not_yet_a_loop():
    calls = [call("a"), call("b"), call("a"), call("b")]
    assert inspect_calls(calls).pattern is Pattern.PROGRESSING


def test_calls_returning_the_same_failure_are_a_loop():
    calls = [
        call("fetch", f'{{"url":"{n}"}}', result="connection refused") for n in range(4)
    ]
    assert inspect_calls(calls).pattern is Pattern.SAME_FAILURE


def test_the_repeated_failure_is_reported():
    calls = [
        call("fetch", f'{{"url":"{n}"}}', result="connection refused") for n in range(4)
    ]
    assert "connection refused" in inspect_calls(calls).reason


def test_an_identical_repeat_outranks_a_repeated_failure():
    calls = [call("fetch", '{"url":"x"}', result="boom")] * 4
    assert inspect_calls(calls).pattern is Pattern.REPEATING


def test_how_many_times_it_repeated_is_reported():
    calls = [call("search", '{"q":"a"}')] * 4
    assert inspect_calls(calls).times == 4


def test_a_run_going_in_circles_should_stop():
    calls = [call("search", '{"q":"a"}')] * 3
    assert inspect_calls(calls).should_stop is True


def test_a_run_making_progress_carries_on():
    assert inspect_calls([call("a"), call("b")]).should_stop is False


def test_what_to_say_to_the_person_is_given():
    calls = [call("search", '{"q":"a"}')] * 3
    assert "search" in inspect_calls(calls).reason


def test_a_progressing_run_needs_no_explanation():
    assert inspect_calls([call("a"), call("b")]).reason == ""


def test_only_recent_calls_are_considered():
    calls = [call("x")] * 3 + [call("a"), call("b"), call("c"), call("d"), call("e")]
    assert inspect_calls(calls, window=5).pattern is Pattern.PROGRESSING


def test_no_calls_at_all_is_progress():
    assert inspect_calls([]).pattern is Pattern.PROGRESSING


def test_a_window_of_nothing_is_refused():
    with pytest.raises(ValueError):
        inspect_calls([call("a")], window=0)
