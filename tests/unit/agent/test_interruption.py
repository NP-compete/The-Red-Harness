"""What to do when someone says something while the agent is working."""

from __future__ import annotations

import pytest

from agent.src.agent.interruption import Handling, Interruption, Running, handle


def running(**kwargs) -> Running:
    defaults = {"stage": "thinking", "tool": "", "reversible": True, "steps_done": 2}
    defaults.update(kwargs)
    return Running(**defaults)


def interruption(**kwargs) -> Interruption:
    defaults = {"text": "also include last quarter", "urgent": False}
    defaults.update(kwargs)
    return Interruption(**defaults)


def test_an_addition_is_folded_into_the_work():
    assert handle(interruption(), running=running()).handling is Handling.FOLDED_IN


def test_a_folded_message_does_not_throw_away_what_is_done():
    assert handle(interruption(), running=running()).keeps_work is True


def test_a_change_of_direction_stops_the_current_work():
    change = interruption(text="actually, forget that and look at expenses instead")
    assert handle(change, running=running()).handling is Handling.REDIRECTED


def test_a_redirect_says_what_is_being_abandoned():
    change = interruption(text="actually, forget that and look at expenses instead")
    assert "2 steps" in handle(change, running=running()).reason


def test_a_stop_request_stops():
    assert (
        handle(interruption(text="stop"), running=running()).handling
        is Handling.STOPPED
    )


def test_a_stop_request_keeps_nothing_running():
    assert handle(interruption(text="stop"), running=running()).continues is False


def test_an_addition_keeps_the_run_going():
    assert handle(interruption(), running=running()).continues is True


def test_a_message_arriving_mid_write_waits_for_the_write_to_finish():
    mid = running(stage="calling-tool", tool="send-email", reversible=False)
    assert (
        handle(interruption(text="stop"), running=mid).applies_after_current_step
        is True
    )


def test_a_message_arriving_while_thinking_applies_at_once():
    assert (
        handle(interruption(text="stop"), running=running()).applies_after_current_step
        is False
    )


def test_a_message_mid_reversible_call_applies_at_once():
    mid = running(stage="calling-tool", tool="search", reversible=True)
    assert (
        handle(interruption(text="stop"), running=mid).applies_after_current_step
        is False
    )


def test_an_urgent_message_is_handled_before_anything_else():
    urgent = interruption(text="also include last quarter", urgent=True)
    assert handle(urgent, running=running()).handling is Handling.STOPPED


def test_an_empty_message_changes_nothing():
    assert (
        handle(interruption(text="   "), running=running()).handling is Handling.IGNORED
    )


def test_an_ignored_message_leaves_the_run_alone():
    assert handle(interruption(text="  "), running=running()).continues is True


def test_a_question_about_the_work_is_answered_without_stopping():
    question = interruption(text="what are you doing?")
    result = handle(question, running=running())
    assert result.handling is Handling.ANSWERED and result.continues is True


def test_a_run_that_has_already_finished_cannot_be_interrupted():
    finished = running(stage="done")
    assert (
        handle(interruption(text="stop"), running=finished).handling
        is Handling.TOO_LATE
    )


def test_an_interruption_of_a_finished_run_says_so():
    finished = running(stage="done")
    assert "already" in handle(interruption(text="stop"), running=finished).reason


def test_a_message_with_no_text_at_all_is_refused():
    with pytest.raises(ValueError):
        Interruption(text="", urgent=False)
