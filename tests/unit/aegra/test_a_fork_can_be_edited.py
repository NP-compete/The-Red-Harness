"""A forked conversation is a conversation, with all that follows."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from agent.aegra.fork_routes import _strip_for_replay
from agent.aegra.truncate_routes import _removals


class TestEveryCopiedMessageCanBeNamed:
    def test_each_one_gets_an_id(self):
        copied = _strip_for_replay(
            [
                {"type": "human", "content": "a", "id": "m1"},
                {"type": "ai", "content": "b", "id": "m2"},
            ]
        )
        assert all(one.get("id") for one in copied)

    def test_a_message_that_arrived_without_one_still_gets_one(self):
        copied = _strip_for_replay([{"type": "human", "content": "a"}])
        assert copied[0].get("id")

    def test_they_are_all_different(self):
        copied = _strip_for_replay(
            [{"type": "human", "content": str(i)} for i in range(5)]
        )
        assert len({one["id"] for one in copied}) == 5


class TestTheOldIdIsStillGone:
    """The reason the ids were being stripped has not changed."""

    def test_the_original_id_is_not_reused(self):
        copied = _strip_for_replay([{"type": "human", "content": "a", "id": "m1"}])
        assert copied[0]["id"] != "m1"

    def test_run_ids_are_still_dropped(self):
        copied = _strip_for_replay([{"type": "ai", "content": "a", "run_id": "r1"}])
        assert "run_id" not in copied[0]


class TestWhatThisUnblocks:
    def test_a_turn_in_a_forked_conversation_can_be_withdrawn(self):
        seeded = _strip_for_replay(
            [
                {"type": "human", "content": "a", "id": "m1"},
                {"type": "ai", "content": "b", "id": "m2"},
            ]
        )
        removals = _removals(seeded, 1)
        assert len(removals) == 1
        assert removals[0]["id"] == seeded[1]["id"]

    def test_the_refusal_still_fires_when_an_id_really_is_missing(self):
        with pytest.raises(HTTPException) as raised:
            _removals([{"type": "human", "content": "a"}], 0)
        assert raised.value.status_code == 409


class TestTheRestOfStrippingIsUnchanged:
    def test_content_survives(self):
        assert (
            _strip_for_replay([{"type": "human", "content": "keep me"}])[0]["content"]
            == "keep me"
        )

    def test_unknown_types_are_still_dropped(self):
        assert _strip_for_replay([{"type": "mystery", "content": "x"}]) == []

    def test_non_dict_entries_are_still_skipped(self):
        assert _strip_for_replay(["not a message", None]) == []
