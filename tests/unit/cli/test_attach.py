"""Picking an answer back up after the connection went (E28-T4)."""

from __future__ import annotations

import pytest

from agent.cli.attach import AttachFailed, attach

FINISHED = {
    "messages": [
        {"type": "human", "content": "q"},
        {"type": "ai", "content": "forty two"},
    ]
}


class _Transport:
    def __init__(self, answers=None, lines=None):
        self.answers = answers or {}
        self.lines = lines or []
        self.sent: list[tuple[str, str]] = []

    def get(self, path: str):
        self.sent.append(("GET", path))
        for key, answer in self.answers.items():
            if key in path:
                return answer
        return 404, {"message": "no such run"}

    def post(self, path: str, body=None):
        self.sent.append(("POST", path))
        raise AssertionError("attaching must not start a run")

    def stream(self, path: str, body=None, method: str = "POST"):
        self.sent.append((method, path))
        yield from self.lines


class TestItNeverStartsARun:
    def test_joining_is_a_get(self):
        transport = _Transport({"/join": (200, FINISHED)})
        attach("t-1", "r-1", transport=transport)
        assert transport.sent == [("GET", "/threads/t-1/runs/r-1/join")]

    def test_so_is_following(self):
        transport = _Transport(
            {"/join": (200, FINISHED)},
            lines=["event: messages/partial", 'data: {"content": "forty two"}'],
        )
        attach("t-1", "r-1", transport=transport, follow=True, write=lambda _p: None)
        assert transport.sent[0] == ("GET", "/threads/t-1/runs/r-1/stream")


class TestWhatComesBack:
    def test_a_finished_run_joins_immediately(self):
        found = attach("t-1", "r-1", transport=_Transport({"/join": (200, FINISHED)}))
        assert found.text == "forty two"
        assert found.thread_id == "t-1"

    def test_an_empty_stream_falls_back_to_the_result(self):
        transport = _Transport({"/join": (200, FINISHED)}, lines=[])
        found = attach(
            "t-1", "r-1", transport=transport, follow=True, write=lambda _p: None
        )
        assert found.text == "forty two"
        assert transport.sent[-1] == ("GET", "/threads/t-1/runs/r-1/join")

    def test_a_pause_comes_back_as_a_pause(self):
        waiting = {
            "messages": [],
            "__interrupt__": [
                {"value": {"action_request": {"name": "send_email", "args": {}}}}
            ],
        }
        found = attach("t-1", "r-1", transport=_Transport({"/join": (200, waiting)}))
        assert found.paused is not None
        assert found.paused["awaiting"][0]["action"] == "send_email"


class TestWhenThereIsNothingToAttachTo:
    def test_an_unknown_run_says_so_rather_than_hanging(self):
        with pytest.raises(AttachFailed, match="not a run on conversation"):
            attach("t-1", "nope", transport=_Transport())

    def test_it_says_how_to_find_the_right_one(self):
        with pytest.raises(AttachFailed, match="run list"):
            attach("t-1", "nope", transport=_Transport())

    def test_a_refused_stream_is_reported_not_swallowed(self):
        class Broken(_Transport):
            def stream(self, path, body=None, method="POST"):
                raise RuntimeError("the agent answered 404 to a stream")

        with pytest.raises(AttachFailed):
            attach("t-1", "r-1", transport=Broken(), follow=True)
