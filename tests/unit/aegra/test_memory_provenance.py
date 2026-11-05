"""Where a remembered fact came from."""

from __future__ import annotations

import pytest

from agent.aegra.personalization_routes import _parse_store_items_to_memories


class _Item:
    def __init__(self, key: str, value: dict) -> None:
        self.key = key
        self.value = value


class TestItTravelsWithTheFact:
    def test_the_conversation_is_reported(self):
        found = _parse_store_items_to_memories(
            [_Item("k1", {"content": "prefers metric", "thread_id": "thread-7"})]
        )
        assert found[0].thread_id == "thread-7"

    def test_every_fact_from_one_item_carries_it(self):
        found = _parse_store_items_to_memories(
            [
                _Item(
                    "k1",
                    {
                        "content": "- likes tea\n- dislikes mornings",
                        "thread_id": "thread-7",
                    },
                )
            ]
        )
        assert len(found) == 2
        assert {one.thread_id for one in found} == {"thread-7"}

    def test_when_it_came_is_still_reported(self):
        found = _parse_store_items_to_memories(
            [_Item("k1", {"content": "x", "created_at": "2026-10-01T09:00:00Z"})]
        )
        assert found[0].created_at == "2026-10-01T09:00:00Z"


class TestWhenItIsNotKnown:
    def test_an_older_entry_says_nothing_rather_than_guessing(self):
        found = _parse_store_items_to_memories([_Item("k1", {"content": "x"})])
        assert found[0].thread_id is None

    @pytest.mark.parametrize("odd", [None, 7, [], {}])
    def test_a_value_it_cannot_read_is_treated_as_unknown(self, odd):
        found = _parse_store_items_to_memories(
            [_Item("k1", {"content": "x", "thread_id": odd})]
        )
        assert found[0].thread_id is None


class TestTheRestIsUnchanged:
    def test_the_fact_itself_still_arrives(self):
        found = _parse_store_items_to_memories(
            [_Item("k1", {"content": "prefers tea"})]
        )
        assert found[0].content == "prefers tea"

    def test_ids_are_still_stable(self):
        once = _parse_store_items_to_memories([_Item("k1", {"content": "prefers tea"})])
        twice = _parse_store_items_to_memories(
            [_Item("k1", {"content": "prefers tea"})]
        )
        assert once[0].id == twice[0].id

    def test_an_empty_line_is_still_not_a_fact(self):
        found = _parse_store_items_to_memories(
            [_Item("k1", {"content": "prefers tea\n\n\n"})]
        )
        assert len(found) == 1
