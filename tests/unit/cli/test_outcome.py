"""Reading what a run came back with, in one place."""

from __future__ import annotations

import pytest

from agent.cli.outcome import RunFailedInBody, outcome_of

ANSWERED = {"messages": [{"type": "ai", "content": "The limit is 750."}]}
PAUSED = {"interrupts": [{"value": {"action_requests": [{"name": "write_file"}]}}]}
CRASHED = {"__error__": {"error": "TypeError", "message": "execution failed"}}


class TestARunThatAnswered:
    def test_the_answer_comes_back(self):
        assert outcome_of(ANSWERED, thread_id="t1").text == "The limit is 750."

    def test_it_is_not_marked_as_waiting(self):
        assert outcome_of(ANSWERED, thread_id="t1").paused is None


class TestARunThatIsWaiting:
    def test_it_is_marked_as_waiting(self):
        assert outcome_of(PAUSED, thread_id="t1").paused is not None

    def test_it_carries_no_answer(self):
        assert outcome_of(PAUSED, thread_id="t1").text == ""


class TestARunThatFailedInsideASuccess:
    """The status says 200 and the body says it threw."""

    def test_it_raises_rather_than_reporting_silence(self):
        with pytest.raises(RunFailedInBody):
            outcome_of(CRASHED, thread_id="t1")

    def test_the_message_is_carried_through(self):
        with pytest.raises(RunFailedInBody, match="execution failed"):
            outcome_of(CRASHED, thread_id="t1")

    def test_an_empty_error_object_still_fails(self):
        with pytest.raises(RunFailedInBody):
            outcome_of({"__error__": {}}, thread_id="t1")

    def test_a_failure_wins_over_a_pause(self):
        both = {**CRASHED, **PAUSED}
        with pytest.raises(RunFailedInBody):
            outcome_of(both, thread_id="t1")


class TestARunThatSaidNothing:
    def test_it_is_reported_as_that_and_not_as_an_answer(self):
        from agent.cli.outcome import NoAnswer

        with pytest.raises(NoAnswer):
            outcome_of({"messages": []}, thread_id="t1")

    def test_an_unreadable_reply_is_not_an_answer_either(self):
        from agent.cli.outcome import NoAnswer

        with pytest.raises(NoAnswer):
            outcome_of("not a reply", thread_id="t1")


class TestBothDoorsUseIt:
    """The drift this exists to prevent, asserted."""

    def test_asking_reads_the_reply_through_it(self):
        import inspect

        from agent.cli import ask

        assert "outcome_of" in inspect.getsource(ask)

    def test_resuming_reads_the_reply_through_it(self):
        import inspect

        from agent.cli import resume

        assert "outcome_of" in inspect.getsource(resume)
