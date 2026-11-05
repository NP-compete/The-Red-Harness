"""Dropping the turns after an edited question."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from agent.aegra.truncate_routes import _removals


def msg(mid: str, kind: str = "human") -> dict:
    return {"id": mid, "type": kind, "content": "x"}


class TestWhatIsRemoved:
    def test_drops_the_edited_question_and_everything_after_it(self):
        kept = [msg("a"), msg("b", "ai"), msg("c"), msg("d", "ai")]
        assert [r["id"] for r in _removals(kept, 2)] == ["c", "d"]

    def test_marks_each_one_for_removal(self):
        assert _removals([msg("a"), msg("b")], 0)[0]["type"] == "remove"

    def test_keeps_everything_before_the_edit(self):
        kept = [msg("a"), msg("b", "ai"), msg("c")]
        assert "a" not in [r["id"] for r in _removals(kept, 2)]

    def test_an_index_past_the_end_removes_nothing(self):
        assert _removals([msg("a")], 5) == []

    def test_removing_from_the_start_removes_everything(self):
        assert len(_removals([msg("a"), msg("b")], 0)) == 2

    def test_a_message_with_no_id_cannot_be_removed_and_is_refused(self):
        """Silently keeping it would leave the withdrawn turn on screen."""
        with pytest.raises(HTTPException) as exc:
            _removals([msg("a"), {"type": "human", "content": "x"}], 1)
        assert exc.value.status_code == 409

    def test_a_negative_index_is_refused_rather_than_wrapping(self):
        with pytest.raises(HTTPException) as exc:
            _removals([msg("a"), msg("b")], -1)
        assert exc.value.status_code == 400


class TestTheShapeTheStateApiAccepts:
    """Coercion pops `type` and then insists on `content`."""

    def test_each_removal_carries_content(self):
        assert _removals([msg("a")], 0)[0]["content"] == ""

    def test_each_removal_still_says_which_message(self):
        assert _removals([msg("a")], 0)[0]["id"] == "a"
