"""E33-T2. The timeline: order, threads, reactions, pins."""

from __future__ import annotations

import datetime as dt
import inspect

import pytest

from agent.src.spaces import timeline
from agent.src.spaces.errors import SpaceRefused


def _row(**over):
    base = {
        "seq": 7,
        "id": "11111111-1111-1111-1111-111111111111",
        "space_id": "22222222-2222-2222-2222-222222222222",
        "author": "ada",
        "body": "hello",
        "reply_to": None,
        "pinned_by": None,
        "created_at": dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    }
    base.update(over)
    return base


class TestOrderIsASequence:
    def test_the_timeline_is_ordered_by_seq_not_by_time(self):
        source = inspect.getsource(timeline.read)
        assert "ORDER BY seq" in source
        assert "created_at" not in source.split("ORDER BY")[1]

    def test_the_cursor_is_a_sequence_comparison(self):
        """`after_seq` resumes from a number the client holds."""
        assert "seq > %s" in inspect.getsource(timeline.read)

    def test_an_empty_page_echoes_the_cursor_back(self):
        """So a client that polls does not have to remember it."""
        assert "else after_seq" in inspect.getsource(timeline.read)


class TestMessageShape:
    def test_a_message_says_whether_it_is_pinned_and_by_whom(self):
        assert _m(_row())["pinned"] is False
        pinned = _m(_row(pinned_by="ada"))
        assert pinned["pinned"] is True
        assert pinned["pinned_by"] == "ada"

    def test_a_reply_is_a_parent_id_not_a_nested_structure(self):
        out = _m(_row(reply_to="33333333-3333-3333-3333-333333333333"))
        assert out["reply_to"].endswith("3333")
        assert "children" not in out
        assert "replies" not in out

    def test_reactions_default_to_none_rather_than_absent(self):
        """A screen rendering a message should not branch on a key."""
        assert _m(_row())["reactions"] == {}


def _m(row):
    return timeline._message(row)


class TestRefusals:
    async def test_an_empty_message_is_refused_before_the_database(self):
        with pytest.raises(SpaceRefused, match="needs something in it"):
            await timeline.post("s1", author="ada", body="   ")

    async def test_an_overlong_message_is_refused(self):
        with pytest.raises(SpaceRefused, match=str(timeline.MAX_BODY)):
            await timeline.post("s1", author="ada", body="x" * (timeline.MAX_BODY + 1))

    async def test_a_reaction_needs_a_short_emoji(self):
        with pytest.raises(SpaceRefused, match="short emoji"):
            await timeline.react("m1", space_id="s1", caller="ada", emoji="")
        with pytest.raises(SpaceRefused, match="short emoji"):
            await timeline.react(
                "m1", space_id="s1", caller="ada", emoji="x" * (timeline.MAX_EMOJI + 1)
            )


class TestMembershipIsAskedNotStored:
    def test_every_entry_point_requires_membership(self):
        """SEC-3: the directory is asked, on each read and each write."""
        for name in ("post", "read", "react", "unreact", "set_pin", "pins"):
            source = inspect.getsource(getattr(timeline, name))
            assert "_require_member" in source, name

    def test_an_outsider_gets_the_same_error_as_a_missing_space(self):
        """Otherwise the error is a directory of every room."""
        source = inspect.getsource(timeline._require_member)
        assert "No such space." in source

    def test_a_reaction_cannot_be_removed_on_somebody_elses_behalf(self):
        """Keyed on the caller, not checked against them."""
        assert "reactor = %s" in inspect.getsource(timeline.unreact)
