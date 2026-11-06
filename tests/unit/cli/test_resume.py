"""Answering a run that stopped for a decision."""

from __future__ import annotations

import pytest

from agent.cli.resume import ResumeFailed, resume_run

ANSWERED = (200, {"messages": [{"type": "ai", "content": "Written."}]})


class _Transport:
    def __init__(self, reply=ANSWERED):
        self._reply = reply
        self.sent: list[tuple[str, dict]] = []

    def post(self, path, body=None):
        self.sent.append((path, body or {}))
        return self._reply

    def get(self, path):
        return 404, {}


class TestSendingADecision:
    def test_it_runs_against_the_same_conversation(self):
        transport = _Transport()
        resume_run("t1", "approve", transport=transport)
        assert transport.sent[0][0] == "/threads/t1/runs/wait"

    def test_it_sends_a_resume_rather_than_a_new_question(self):
        transport = _Transport()
        resume_run("t1", "approve", transport=transport)
        assert "command" in transport.sent[0][1]
        assert "input" not in transport.sent[0][1]

    def test_it_carries_the_decision(self):
        transport = _Transport()
        resume_run("t1", "approve", transport=transport)
        sent = transport.sent[0][1]["command"]["resume"]
        assert sent["decisions"][0]["type"] == "approve"

    def test_it_returns_what_the_agent_said_afterwards(self):
        assert resume_run("t1", "approve", transport=_Transport()).text == "Written."


class TestRejecting:
    def test_a_rejection_is_sent_as_one(self):
        transport = _Transport()
        resume_run("t1", "reject", transport=transport)
        assert (
            transport.sent[0][1]["command"]["resume"]["decisions"][0]["type"]
            == "reject"
        )

    def test_a_reason_travels_with_it(self):
        transport = _Transport()
        resume_run("t1", "reject", transport=transport, message="not that file")
        sent = transport.sent[0][1]["command"]["resume"]["decisions"][0]
        assert sent["message"] == "not that file"


class TestDecisionsItWillNotSend:
    def test_an_unknown_decision_is_refused_before_anything_is_sent(self):
        transport = _Transport()
        with pytest.raises(ResumeFailed, match="maybe"):
            resume_run("t1", "maybe", transport=transport)
        assert transport.sent == []

    def test_the_refusal_names_what_is_allowed(self):
        with pytest.raises(ResumeFailed, match="approve"):
            resume_run("t1", "maybe", transport=_Transport())


class TestWhenItGoesWrong:
    def test_a_refusal_is_reported(self):
        transport = _Transport(reply=(409, {"detail": "nothing is waiting"}))
        with pytest.raises(ResumeFailed, match="nothing is waiting"):
            resume_run("t1", "approve", transport=transport)

    def test_a_run_that_pauses_again_is_reported_as_waiting(self):
        paused = (
            200,
            {"interrupts": [{"value": {"action_requests": [{"name": "execute_sql"}]}}]},
        )
        found = resume_run("t1", "approve", transport=_Transport(reply=paused))
        assert found.paused["awaiting"][0]["action"] == "execute_sql"

    def test_a_run_that_says_nothing_is_not_reported_as_an_answer(self):
        transport = _Transport(reply=(200, {"messages": []}))
        with pytest.raises(ResumeFailed):
            resume_run("t1", "approve", transport=transport)


class TestWhenTheReplyCarriesNoTranscript:
    """The agent accepted it; the reply just does not repeat itself."""

    class _Transport:
        def __init__(self, state):
            self._state = state
            self.asked: list[str] = []

        def post(self, path, body=None):
            self.asked.append(f"POST {path}")
            return 200, {}

        def get(self, path):
            self.asked.append(f"GET {path}")
            return 200, self._state

    def test_it_reads_the_conversation_rather_than_giving_up(self):
        state = {"values": {"messages": [{"type": "ai", "content": "Written."}]}}
        transport = self._Transport(state)
        assert resume_run("t1", "approve", transport=transport).text == "Written."

    def test_it_only_looks_when_the_reply_was_empty(self):
        from agent.cli.resume import resume_run as send

        class _Full:
            def post(self, path, body=None):
                return 200, {"messages": [{"type": "ai", "content": "Written."}]}

            def get(self, path):
                raise AssertionError("should not need the conversation")

        assert send("t1", "approve", transport=_Full()).text == "Written."

    def test_a_pause_in_the_stored_conversation_is_not_trusted(self):
        state = {
            "interrupts": [{"value": {"action_requests": [{"name": "execute_sql"}]}}],
            "values": {"messages": [{"type": "ai", "content": "Written."}]},
        }
        found = resume_run("t1", "approve", transport=self._Transport(state))
        assert found.paused is None
        assert found.text == "Written."

    def test_a_pause_in_the_reply_is_trusted(self):
        paused = (
            200,
            {"interrupts": [{"value": {"action_requests": [{"name": "execute_sql"}]}}]},
        )
        found = resume_run("t1", "approve", transport=_Transport(reply=paused))
        assert found.paused["awaiting"][0]["action"] == "execute_sql"

    def test_a_conversation_it_cannot_read_is_reported_honestly(self):
        class _Gone:
            def post(self, path, body=None):
                return 200, {}

            def get(self, path):
                return 404, {"detail": "gone"}

        with pytest.raises(ResumeFailed):
            resume_run("t1", "approve", transport=_Gone())


class TestAFailureHiddenInsideASuccess:
    """200 with an error in the body is not a success."""

    class _Transport:
        def __init__(self, body):
            self._body = body

        def post(self, path, body=None):
            return 200, self._body

        def get(self, path):
            raise AssertionError("should not look further after an error")

    def test_it_is_reported_as_a_failure(self):
        body = {"__error__": {"error": "TypeError", "message": "execution failed"}}
        with pytest.raises(ResumeFailed):
            resume_run("t1", "approve", transport=self._Transport(body))

    def test_the_message_is_carried_through(self):
        body = {"__error__": {"error": "TypeError", "message": "execution failed"}}
        with pytest.raises(ResumeFailed, match="execution failed"):
            resume_run("t1", "approve", transport=self._Transport(body))

    def test_an_error_with_no_message_still_fails(self):
        with pytest.raises(ResumeFailed):
            resume_run("t1", "approve", transport=self._Transport({"__error__": {}}))
