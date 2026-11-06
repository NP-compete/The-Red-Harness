"""Forking at a point the conversation has since been shortened past."""

from __future__ import annotations

from typing import Any

from agent.aegra.fork_routes import messages_for_fork


def _m(id_: str, text: str, type_: str = "human") -> dict[str, Any]:
    return {"id": id_, "type": type_, "content": text}


ORIGINAL = [_m(f"m{i}", f"turn {i}") for i in range(20)]
SUMMARY = _m("s1", "Earlier turns, summarised.", "ai")
SHORTENED = [SUMMARY, *ORIGINAL[16:]]

HISTORY = [
    {"checkpoint_id": "c2", "values": {"messages": SHORTENED}},
    {"checkpoint_id": "c1", "values": {"messages": ORIGINAL}},
]


class TestTheCutLandsWhereSomebodyPointed:
    def test_it_ends_on_the_message_that_was_clicked(self):
        found = messages_for_fork(HISTORY, 3)
        assert found[-1]["id"] == "m17"

    def test_it_does_not_cut_by_position_in_the_longer_list(self):
        found = messages_for_fork(HISTORY, 3)
        assert found[-1]["id"] != "m2"


class TestTheTextComesBackWhole:
    def test_everything_before_the_cut_is_the_original_text(self):
        found = messages_for_fork(HISTORY, 3)
        assert [one["id"] for one in found] == [f"m{i}" for i in range(18)]

    def test_the_summary_is_not_in_it(self):
        found = messages_for_fork(HISTORY, 3)
        assert all(one["id"] != "s1" for one in found)

    def test_the_earliest_turn_is_there(self):
        found = messages_for_fork(HISTORY, 3)
        assert found[0]["content"] == "turn 0"


class TestForkingAtTheSummaryItself:
    def test_it_gives_the_summary_and_does_not_fail(self):
        found = messages_for_fork(HISTORY, 1)
        assert [one["id"] for one in found] == ["s1"]


class TestAThreadThatWasNeverShortened:
    """The ordinary case must be untouched by all of this."""

    def test_the_slice_is_the_slice(self):
        history = [{"checkpoint_id": "c1", "values": {"messages": ORIGINAL}}]
        found = messages_for_fork(history, 3)
        assert [one["id"] for one in found] == ["m0", "m1", "m2"]

    def test_an_index_past_the_end_takes_everything(self):
        history = [{"checkpoint_id": "c1", "values": {"messages": ORIGINAL}}]
        assert len(messages_for_fork(history, 500)) == len(ORIGINAL)

    def test_a_part_written_run_does_not_win_over_the_finished_one(self):
        history = [
            {"checkpoint_id": "c3", "values": {"messages": []}},
            {"checkpoint_id": "c2", "values": {"messages": ORIGINAL}},
        ]
        assert len(messages_for_fork(history, 500)) == len(ORIGINAL)


class TestNothingToFork:
    def test_no_history_gives_nothing(self):
        assert messages_for_fork([], 3) == []

    def test_position_zero_gives_nothing(self):
        assert messages_for_fork(HISTORY, 0) == []

    def test_a_negative_position_gives_nothing(self):
        assert messages_for_fork(HISTORY, -1) == []


class TestMessagesWithNoIds:
    def test_it_falls_back_to_what_was_shown(self):
        shown = [{"type": "human", "content": "a"}, {"type": "ai", "content": "b"}]
        history = [{"checkpoint_id": "c1", "values": {"messages": shown}}]
        assert messages_for_fork(history, 1) == [shown[0]]


class TestTheCheckCanFail:
    def test_the_two_lists_really_do_disagree(self):
        assert SHORTENED[2]["id"] != ORIGINAL[2]["id"]
