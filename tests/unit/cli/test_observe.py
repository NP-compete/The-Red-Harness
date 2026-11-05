"""Reading an agent's own traces from a terminal."""

from __future__ import annotations

import pytest

from agent.cli.observe import ObserveFailed, collect


class _Transport:
    def __init__(self, threads, states):
        self._threads = threads
        self._states = states
        self.asked: list[str] = []

    def get(self, path):
        self.asked.append(path)
        if path == "/threads":
            return self._threads
        return self._states.get(path, (404, {"detail": "gone"}))


ABANDONED = {
    "values": {
        "messages": [
            {"type": "ai", "content": "", "tool_calls": [{"name": "sql", "id": "c1"}]},
            {"type": "tool", "tool_call_id": "c1", "name": "sql", "content": "42 rows"},
            {"type": "ai", "content": "I cannot answer."},
        ]
    }
}


def _transport(count=1, broken=0):
    threads = [
        {"thread_id": f"t{i}", "created_at": "2026-10-28T10:00:00Z"}
        for i in range(count)
    ]
    states = {f"/threads/t{i}/state": (200, ABANDONED) for i in range(count - broken)}
    return _Transport((200, {"threads": threads}), states)


class TestCollecting:
    def test_it_reads_each_conversation(self):
        transport = _transport(count=3)
        collect(transport=transport, limit=10)
        assert transport.asked.count("/threads") == 1
        assert sum(p.endswith("/state") for p in transport.asked) == 3

    def test_it_returns_what_it_found(self):
        found = collect(transport=_transport(count=2), limit=10)
        assert found.observations[0].seen == 2

    def test_it_says_how_many_it_read(self):
        assert collect(transport=_transport(count=3), limit=10).read == 3

    def test_it_stops_at_the_limit(self):
        transport = _transport(count=5)
        collect(transport=transport, limit=2)
        assert sum(p.endswith("/state") for p in transport.asked) == 2


class TestCoverage:
    def test_a_conversation_it_could_not_read_is_counted(self):
        found = collect(transport=_transport(count=3, broken=2), limit=10)
        assert found.unreadable == 2

    def test_the_ones_it_did_read_are_still_mined(self):
        found = collect(transport=_transport(count=3, broken=2), limit=10)
        assert found.read == 1 and found.observations

    def test_a_listing_it_cannot_get_is_a_failure_not_an_empty_result(self):
        transport = _Transport((403, {"detail": "no"}), {})
        with pytest.raises(ObserveFailed):
            collect(transport=transport, limit=10)


class TestTheWindow:
    def test_it_passes_the_window_through(self):
        transport = _Transport(
            (
                200,
                {
                    "threads": [
                        {"thread_id": "t0", "created_at": "2020-01-01T00:00:00Z"}
                    ]
                },
            ),
            {"/threads/t0/state": (200, ABANDONED)},
        )
        found = collect(transport=transport, limit=10, since="2026-10-01T00:00:00Z")
        assert found.observations == []
