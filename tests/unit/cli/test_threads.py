"""Conversations, from a terminal."""

from __future__ import annotations

import pytest

from agent.cli.threads import (
    ThreadFailed,
    fork_thread,
    list_threads,
    remove_thread,
    show_thread,
)


class _Transport:
    def __init__(self, replies: dict[tuple[str, str], tuple[int, object]]):
        self._replies = replies
        self.calls: list[tuple[str, str]] = []

    def _answer(self, method: str, path: str):
        self.calls.append((method, path))
        try:
            return self._replies[(method, path)]
        except KeyError:
            return 404, {"detail": "not found"}

    def get(self, path: str):
        return self._answer("GET", path)

    def post(self, path: str, body: dict | None = None):
        return self._answer("POST", path)

    def delete(self, path: str):
        return self._answer("DELETE", path)


LISTED = [
    {"thread_id": "t1", "metadata": {"thread_name": "Travel limits"}, "status": "idle"},
    {"thread_id": "t2", "metadata": {}, "status": "busy"},
]


class TestListing:
    def _listed(self, payload=LISTED, status=200):
        transport = _Transport({("GET", "/threads"): (status, payload)})
        return list_threads(transport=transport)

    def test_it_reports_each_conversation(self):
        assert len(self._listed()) == 2

    def test_it_reports_the_identifier(self):
        assert self._listed()[0].thread_id == "t1"

    def test_it_reports_the_name_when_there_is_one(self):
        assert self._listed()[0].title == "Travel limits"

    def test_an_unnamed_conversation_is_not_given_an_invented_name(self):
        assert self._listed()[1].title == ""

    def test_it_reports_what_the_agent_says_about_the_run(self):
        assert self._listed()[1].status == "busy"

    def test_a_refusal_is_not_an_empty_list(self):
        with pytest.raises(ThreadFailed):
            self._listed(payload={"detail": "no"}, status=403)

    def test_the_wrapped_shape_the_agent_actually_returns_is_read(self):
        assert len(self._listed(payload={"threads": LISTED})) == 2

    def test_a_bare_list_is_read_too(self):
        assert len(self._listed(payload=LISTED)) == 2

    def test_a_shape_it_does_not_recognise_is_refused(self):
        with pytest.raises(ThreadFailed):
            self._listed(payload={"threads": "lots"})

    def test_something_that_is_neither_is_refused(self):
        with pytest.raises(ThreadFailed):
            self._listed(payload="everything is fine")


class TestShowing:
    def test_it_returns_what_the_conversation_holds(self):
        transport = _Transport(
            {
                ("GET", "/threads/t1/state"): (
                    200,
                    {"values": {"messages": [{"type": "ai"}]}},
                )
            }
        )
        assert show_thread("t1", transport=transport)["values"]["messages"]

    def test_a_conversation_that_is_not_there_is_reported(self):
        transport = _Transport({})
        with pytest.raises(ThreadFailed, match="t1"):
            show_thread("t1", transport=transport)


class TestRemoving:
    def test_it_asks_the_agent_to_remove_it(self):
        transport = _Transport({("DELETE", "/threads/t1"): (204, {})})
        remove_thread("t1", transport=transport)
        assert ("DELETE", "/threads/t1") in transport.calls

    def test_a_refusal_is_reported_rather_than_swallowed(self):
        transport = _Transport(
            {("DELETE", "/threads/t1"): (403, {"detail": "not yours"})}
        )
        with pytest.raises(ThreadFailed, match="not yours"):
            remove_thread("t1", transport=transport)

    def test_removing_one_that_was_already_gone_is_not_an_error(self):
        transport = _Transport({("DELETE", "/threads/t1"): (404, {})})
        remove_thread("t1", transport=transport)


class TestForking:
    def test_it_asks_the_agent_to_fork(self):
        transport = _Transport(
            {
                ("GET", "/threads/t1/state"): (200, {"values": {"messages": []}}),
                ("POST", "/threads/t1/fork"): (200, {"thread_id": "t2"}),
            }
        )
        assert fork_thread("t1", transport=transport) == "t2"

    def test_it_names_where_to_cut(self):
        sent: dict = {}

        class _Recording(_Transport):
            def post(self, path, body=None):
                sent.update(body or {})
                return super().post(path, body)

        transport = _Recording(
            {
                ("GET", "/threads/t1/state"): (
                    200,
                    {"values": {"messages": [{"type": "human"}, {"type": "ai"}]}},
                ),
                ("POST", "/threads/t1/fork"): (200, {"thread_id": "t2"}),
            }
        )
        fork_thread("t1", transport=transport)
        assert sent.get("message_index") == 2

    def test_a_cut_point_the_caller_gave_is_used_as_given(self):
        sent: dict = {}

        class _Recording(_Transport):
            def post(self, path, body=None):
                sent.update(body or {})
                return super().post(path, body)

        transport = _Recording(
            {("POST", "/threads/t1/fork"): (200, {"thread_id": "t2"})}
        )
        fork_thread("t1", transport=transport, at=1)
        assert sent == {"message_index": 1}

    def test_a_refusal_is_reported(self):
        transport = _Transport(
            {
                ("GET", "/threads/t1/state"): (200, {"values": {"messages": []}}),
                ("POST", "/threads/t1/fork"): (400, {"detail": "nothing to fork"}),
            }
        )
        with pytest.raises(ThreadFailed, match="nothing to fork"):
            fork_thread("t1", transport=transport)
