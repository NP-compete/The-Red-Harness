"""A log line from a run names the conversation (OBS-1, OBS-3)."""

from __future__ import annotations

import pytest

from agent.aegra.http_app import _thread_in


class TestWhereThereIsAThread:
    @pytest.mark.parametrize(
        "path",
        [
            "/threads/abc-123/runs/stream",
            "/threads/abc-123/runs/wait",
            "/threads/abc-123/state",
            "/threads/abc-123/share",
            "/threads/abc-123/messages",
            "/threads/abc-123",
        ],
    )
    def test_it_is_found(self, path):
        assert _thread_in(path) == "abc-123"

    def test_an_id_with_a_uuid_shape(self):
        assert (
            _thread_in("/threads/0cb221b5-59f4-49e5-9371-2861ab98a37f/runs/wait")
            == "0cb221b5-59f4-49e5-9371-2861ab98a37f"
        )


class TestWhereThereIsNot:
    @pytest.mark.parametrize(
        "path",
        [
            "/health",
            "/threads",
            "/config/tree",
            "/spaces/a-room/messages",
            "/v1/eval/thread-shape/t1",
        ],
    )
    def test_nothing_is_bound(self, path):
        assert _thread_in(path) is None


class TestItReachesTheLogContext:
    def test_a_bound_thread_comes_out_on_a_log_event(self):
        """Through the processor every log line goes through."""
        from agent.utils.pylogger import (
            _inject_request_context,
            bind_request_context,
            clear_request_context,
        )

        try:
            bind_request_context(thread_id=_thread_in("/threads/t-9/runs/wait"))
            said = _inject_request_context(None, "info", {"event": "something"})
            assert said["thread_id"] == "t-9"
        finally:
            clear_request_context()

    def test_and_is_absent_when_there_is_no_thread(self):
        from agent.utils.pylogger import (
            _inject_request_context,
            bind_request_context,
            clear_request_context,
        )

        try:
            bind_request_context(thread_id=_thread_in("/health"))
            said = _inject_request_context(None, "info", {"event": "something"})
            assert "thread_id" not in said
        finally:
            clear_request_context()

    def test_the_middleware_asks_for_it(self):
        """The wiring, not the helper."""
        import inspect

        from agent.aegra.http_app import RequestContextMiddleware

        source = inspect.getsource(RequestContextMiddleware)
        assert "thread_id=_thread_in(" in source, (
            "the middleware no longer binds the thread. Every log line from "
            "a run goes back to naming the trace and the user and not the "
            "conversation."
        )
