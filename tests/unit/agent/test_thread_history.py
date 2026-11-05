"""Reading the shape of a conversation's history."""

from __future__ import annotations

from typing import Any

from agent.src.agent.thread_history import (
    high_water_mark,
    shown_messages,
    was_shortened,
)


def _m(id_: str) -> dict[str, Any]:
    return {"id": id_, "type": "human", "content": id_}


def _at(checkpoint: str, messages: list[dict]) -> dict[str, Any]:
    return {"checkpoint_id": checkpoint, "values": {"messages": messages}}


FULL = [_m(f"m{i}") for i in range(20)]
SHORTENED = [_m("s1"), *FULL[16:]]

AFTER_SHORTENING = [_at("c2", SHORTENED), _at("c1", FULL)]
NEVER_SHORTENED = [_at("c2", FULL), _at("c1", FULL[:4])]


class TestWhatTheConversationIsNow:
    def test_it_is_the_newest_entry(self):
        assert len(shown_messages(AFTER_SHORTENING)) == 5

    def test_an_entry_written_before_any_message_is_skipped(self):
        history = [_at("c3", []), _at("c2", FULL)]
        assert len(shown_messages(history)) == 20

    def test_no_history_is_nothing(self):
        assert shown_messages([]) == []


class TestTheMostItEverHeld:
    def test_it_is_the_longest_entry(self):
        assert high_water_mark(AFTER_SHORTENING) == 20

    def test_it_is_the_current_length_when_nothing_was_removed(self):
        assert high_water_mark(NEVER_SHORTENED) == 20

    def test_no_history_is_zero(self):
        assert high_water_mark([]) == 0


class TestWhetherItWasShortened:
    def test_a_shortened_thread_says_so(self):
        assert was_shortened(AFTER_SHORTENING)

    def test_a_thread_that_only_ever_grew_does_not(self):
        assert not was_shortened(NEVER_SHORTENED)

    def test_a_brand_new_thread_does_not(self):
        assert not was_shortened([_at("c1", [])])

    def test_no_history_does_not(self):
        assert not was_shortened([])


class TestWhatShorteningDoesNotDistinguish:
    """It means "messages were removed", not "summarised"."""

    def test_a_withdrawn_turn_reads_as_a_shortening(self):
        history = [_at("c2", FULL[:3]), _at("c1", FULL[:4])]
        assert was_shortened(history)


class TestTheTwoAnswersAreNotTheSameAnswer:
    """The confusion this module exists to stop."""

    def test_they_differ_once_a_thread_is_shortened(self):
        assert len(shown_messages(AFTER_SHORTENING)) != high_water_mark(
            AFTER_SHORTENING
        )

    def test_they_agree_when_nothing_was_removed(self):
        assert len(shown_messages(NEVER_SHORTENED)) == high_water_mark(NEVER_SHORTENED)


class TestItSurvivesHistoryItDoesNotRecognise:
    def test_an_entry_with_no_values(self):
        assert shown_messages([{"checkpoint_id": "c1"}, _at("c0", FULL)]) == FULL

    def test_messages_that_are_not_mappings(self):
        history = [_at("c1", ["not a message", None])]  # type: ignore[list-item]
        assert len(shown_messages(history)) == 2
        assert high_water_mark(history) == 2
