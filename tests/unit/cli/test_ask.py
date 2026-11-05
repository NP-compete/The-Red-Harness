"""Asking a question from a script."""

from __future__ import annotations

import pytest

from agent.cli.ask import AskFailed, answer_from, ask


class _Transport:
    """Stands in for the agent, recording what it was asked."""

    def __init__(self, replies: list[tuple[int, dict]]):
        self._replies = list(replies)
        self.calls: list[tuple[str, str, dict | None]] = []

    def post(self, path: str, body: dict | None = None):
        self.calls.append(("POST", path, body))
        status, payload = self._replies.pop(0)
        return status, payload


def _run(question="what is the limit?", replies=None, **kwargs):
    replies = replies or [
        (200, {"thread_id": "t1"}),
        (
            200,
            {
                "messages": [
                    {"type": "human", "content": "q"},
                    {"type": "ai", "content": "The limit is 750."},
                ]
            },
        ),
    ]
    transport = _Transport(replies)
    said = ask(question, transport=transport, **kwargs)
    return said, transport


class TestAskingOnce:
    def test_it_makes_a_thread(self):
        _, transport = _run()
        assert transport.calls[0][1] == "/threads"

    def test_it_runs_the_question_on_that_thread(self):
        _, transport = _run()
        assert transport.calls[1][1] == "/threads/t1/runs/wait"

    def test_it_sends_the_question(self):
        _, transport = _run("what is the limit?")
        sent = transport.calls[1][2] or {}
        assert "what is the limit?" in str(sent)

    def test_it_returns_what_the_agent_said(self):
        said, _ = _run()
        assert said.text == "The limit is 750."

    def test_it_reports_the_thread_so_the_caller_can_follow_up(self):
        said, _ = _run()
        assert said.thread_id == "t1"


class TestWhenTheThreadCannotBeMade:
    def test_it_fails_rather_than_carrying_on(self):
        with pytest.raises(AskFailed):
            _run(replies=[(503, {"detail": "no"})])

    def test_it_says_what_went_wrong(self):
        with pytest.raises(AskFailed, match="503"):
            _run(replies=[(503, {"detail": "no"})])

    def test_it_does_not_try_to_run_anything(self):
        transport = _Transport([(503, {"detail": "no"})])
        with pytest.raises(AskFailed):
            ask("q", transport=transport)
        assert len(transport.calls) == 1


class TestWhenTheRunFails:
    def test_it_fails(self):
        with pytest.raises(AskFailed):
            _run(replies=[(200, {"thread_id": "t1"}), (500, {"detail": "boom"})])

    def test_it_carries_what_the_agent_said_about_it(self):
        with pytest.raises(AskFailed, match="boom"):
            _run(replies=[(200, {"thread_id": "t1"}), (500, {"detail": "boom"})])


class TestWhenTheRunStopsForApproval:
    """Unattended, there is nobody to approve it."""

    def test_it_is_not_reported_as_an_answer(self):
        paused = (200, {"__interrupt__": [{"value": "approve?"}], "messages": []})
        said, _ = _run(replies=[(200, {"thread_id": "t1"}), paused])
        assert said.text == ""

    def test_it_says_the_run_is_waiting(self):
        paused = (200, {"__interrupt__": [{"value": "approve?"}], "messages": []})
        said, _ = _run(replies=[(200, {"thread_id": "t1"}), paused])
        assert said.paused["status"] == "needs_approval"


class TestReadingTheAnswer:
    def test_the_last_thing_the_agent_said_is_the_answer(self):
        messages = [
            {"type": "ai", "content": "thinking"},
            {"type": "tool", "content": "data"},
            {"type": "ai", "content": "the answer"},
        ]
        assert answer_from({"messages": messages}) == "the answer"

    def test_a_question_nobody_answered_is_not_an_empty_string(self):
        assert answer_from({"messages": [{"type": "human", "content": "q"}]}) is None

    def test_content_in_parts_is_joined(self):
        messages = [
            {
                "type": "ai",
                "content": [
                    {"type": "text", "text": "two "},
                    {"type": "text", "text": "parts"},
                ],
            }
        ]
        assert answer_from({"messages": messages}) == "two parts"

    def test_a_shape_it_does_not_know_is_not_guessed_at(self):
        assert answer_from({"messages": [{"type": "ai", "content": 42}]}) is None

    def test_no_messages_at_all_is_not_an_answer(self):
        assert answer_from({}) is None


class TestAPausedRunIsItsOwnOutcome:
    """Not a failure, and not an answer: work waiting on somebody."""

    PAUSED = (
        200,
        {
            "__interrupt__": [
                {
                    "value": {
                        "action_request": {"action": "execute_sql", "args": {}},
                        "description": "Run this query?",
                    }
                }
            ],
            "messages": [],
        },
    )

    def _ask(self):
        from agent.cli.ask import ask

        transport = _Transport([(200, {"thread_id": "t1"}), self.PAUSED])
        return ask("q", transport=transport)

    def test_it_is_not_raised_as_a_failure(self):
        self._ask()

    def test_it_says_it_is_waiting(self):
        assert self._ask().paused is not None

    def test_it_names_what_is_waiting(self):
        assert self._ask().paused["awaiting"][0]["action"] == "execute_sql"

    def test_it_says_how_to_continue(self):
        assert self._ask().paused["resume"]["thread_id"] == "t1"

    def test_the_text_is_not_presented_as_an_answer(self):
        assert self._ask().text == ""

    def test_an_answered_run_is_not_marked_as_waiting(self):
        said, _ = _run()
        assert said.paused is None
