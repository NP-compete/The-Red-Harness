"""E33-T2. The room, pushed rather than polled."""

from __future__ import annotations

import inspect

from agent.aegra import space_routes


def _source() -> str:
    return inspect.getsource(space_routes.stream_timeline)


class TestMembershipIsNotCheckedOnceAtConnect:
    def test_the_loop_reads_through_the_membership_check(self):
        """An open stream is a standing read."""
        body = _source()
        after_loop = body.split("while True:")[1]
        assert "timeline.read" in after_loop

    def test_losing_membership_ends_the_stream(self):
        assert "not_a_member" in _source()


class TestAStreamDoesNotLiveForEver:
    def test_it_stops_on_its_own(self):
        assert space_routes.STREAM_MAX_SECONDS <= 60 * 60
        assert "STREAM_MAX_SECONDS" in _source()

    def test_it_says_end_rather_than_dropping(self):
        """So a client reconnects instead of backing off."""
        assert "event: end" in _source()

    def test_it_stops_when_the_client_has_gone(self):
        assert "is_disconnected" in _source()

    def test_it_speaks_when_the_room_is_quiet(self):
        """A silent connection is closed by proxies, and the client"""
        assert space_routes.STREAM_HEARTBEAT_SECONDS > space_routes.STREAM_TICK_SECONDS
        assert ": still here" in _source()


class TestTheCursorIsTheWholeContract:
    def test_it_resumes_from_a_sequence_the_client_sent(self):
        signature = inspect.signature(space_routes.stream_timeline)
        assert signature.parameters["after_seq"].default == 0

    def test_the_end_frame_carries_the_cursor_back(self):
        """A reconnect needs no state the client does not already hold."""
        assert "next_seq" in _source()

    def test_a_non_member_never_reaches_the_stream(self):
        assert "_member_or_404" in _source()
