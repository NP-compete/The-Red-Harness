"""Withdrawing turns from a conversation that has been shortened."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from agent.aegra.truncate_routes import _removals
from agent.src.agent.thread_history import shown_messages


def _m(id_: str, type_: str = "human") -> dict[str, Any]:
    return {"id": id_, "type": type_, "content": id_}


ORIGINAL = [_m(f"m{i}") for i in range(20)]
SUMMARY = _m("s1", "ai")
SHORTENED = [SUMMARY, *ORIGINAL[16:]]

HISTORY = [
    {"checkpoint_id": "c2", "values": {"messages": SHORTENED}},
    {"checkpoint_id": "c1", "values": {"messages": ORIGINAL}},
]


def _withdraw(history: list[dict], message_index: int) -> list[str]:
    """Ids the server would remove, through the path the route uses."""
    return [one["id"] for one in _removals(shown_messages(history), message_index)]


class TestWithdrawingTheLastTwoTurns:
    def test_exactly_two_turns_go(self):
        assert _withdraw(HISTORY, 3) == ["m18", "m19"]

    def test_the_turns_that_stay_are_not_touched(self):
        gone = _withdraw(HISTORY, 3)
        for kept in ("s1", "m16", "m17"):
            assert kept not in gone

    def test_it_does_not_sweep_the_whole_visible_tail(self):
        gone = _withdraw(HISTORY, 3)
        assert "m16" not in gone
        assert len(gone) == 2


class TestWithdrawingEverything:
    def test_position_zero_removes_what_is_showing_and_no_more(self):
        assert _withdraw(HISTORY, 0) == ["s1", "m16", "m17", "m18", "m19"]


class TestAThreadThatWasNeverShortened:
    def test_it_behaves_exactly_as_before(self):
        history = [{"checkpoint_id": "c1", "values": {"messages": ORIGINAL}}]
        assert _withdraw(history, 18) == ["m18", "m19"]


class TestTheRefusalsStillHold:
    def test_a_turn_with_no_id_refuses_rather_than_half_deleting(self):
        shown = [_m("m0"), {"type": "ai", "content": "no id"}]
        with pytest.raises(HTTPException) as raised:
            _removals(shown, 0)
        assert raised.value.status_code == 409

    def test_a_negative_position_is_refused(self):
        with pytest.raises(HTTPException) as raised:
            _removals(SHORTENED, -1)
        assert raised.value.status_code == 400


class TestTheRouteUsesIt:
    """A helper beside the route is not the route."""

    def test_the_route_counts_against_what_was_shown(self):
        import inspect

        from agent.aegra import truncate_routes

        source = inspect.getsource(truncate_routes.truncate_thread)
        assert "shown_messages" in source
        assert "_latest_messages" not in source


class TestTheCheckCanFail:
    def test_the_two_lists_disagree_at_this_position(self):
        assert SHORTENED[3]["id"] != ORIGINAL[3]["id"]
