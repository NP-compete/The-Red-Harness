"""E33-T3. When a room's message is for the agent."""

from __future__ import annotations

import pytest

from agent.src.spaces.addressing import addresses_agent

HANDLE = "workpilot"


def ask(text: str, *, always_on: bool = False):
    return addresses_agent(text, handle=HANDLE, always_on=always_on)


class TestTagged:
    @pytest.mark.parametrize(
        "text",
        [
            "@workpilot what happened?",
            "@workpilot, please",
            "@workpilot: status?",
            "ask @Workpilot about it",
            "(@workpilot)",
            "@workpilot",
        ],
    )
    def test_a_mention_wakes_it(self, text):
        assert ask(text).addressed
        assert ask(text).reason == "tagged"

    @pytest.mark.parametrize(
        "text",
        [
            "can someone look at this",
            "",
            "mail support@workpilot.example",
            "see notes@workpilot.example for the log",
            "@work is a different thing",
            "@workpilots is somebody else",
            "workpilot usually handles this",
        ],
    )
    def test_everything_else_does_not(self, text):
        assert not ask(text).addressed
        assert ask(text).reason == "not_addressed"


class TestAlwaysOn:
    def test_an_always_on_room_answers_anything(self):
        assert ask("no handle here", always_on=True).addressed

    def test_the_reason_says_always_on_even_when_also_tagged(self):
        """A screen explaining why the agent replied should not say"""
        assert ask("@workpilot hello", always_on=True).reason == "always_on"

    def test_it_is_off_unless_asked_for(self):
        assert not ask("no handle here").addressed


def test_no_handle_configured_means_no_mentions():
    """Rather than matching a bare `@`, which every email address"""
    assert not addresses_agent("@ hello", handle="").addressed
