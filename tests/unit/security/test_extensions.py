"""E37-T1/T2. The vocabulary an extension speaks."""

from __future__ import annotations

import dataclasses

from agent.src.security.extensions import (
    HookPoint,
    Payload,
    Refused,
    Rewritten,
    Unchanged,
    read_outcome,
)


class TestWhatAnExtensionMaySee:
    def test_the_payload_carries_no_credentials(self):
        """An extension that cannot see a credential cannot leak"""
        fields = {f.name for f in dataclasses.fields(Payload)}
        assert fields == {"text", "tool", "subject", "point"}
        assert not any(
            word in name for name in fields for word in ("token", "secret", "key")
        )

    def test_the_wire_form_names_the_point(self):
        """So one url can serve all four and branch on it."""
        said = Payload(text="hi", point=HookPoint.AFTER_TOOL).as_json()
        assert said["point"] == "after_tool"
        assert said["text"] == "hi"

    def test_there_are_four_points(self):
        assert [p.value for p in HookPoint] == [
            "before_model",
            "after_model",
            "before_tool",
            "after_tool",
        ]


class TestWhatAnExtensionMaySay:
    def test_three_answers_and_approval_is_not_one(self):
        """It may leave the text, rewrite it, or refuse. There is"""
        assert read_outcome({"verdict": "unchanged"}) == Unchanged()
        assert read_outcome({"verdict": "rewritten", "text": "x"}) == Rewritten("x")
        assert read_outcome({"verdict": "refused", "reason": "no"}) == Refused("no")

    def test_a_refusal_always_has_a_reason(self):
        assert read_outcome({"verdict": "refused"}).reason == "no reason given"

    def test_an_unreadable_reply_is_not_a_pass(self):
        """`{"ok": true}` by accident must not read as "checked"."""
        assert read_outcome({"ok": True}) is None
        assert read_outcome({"verdict": "approved"}) is None
        assert read_outcome("yes") is None

    def test_rewritten_with_no_text_is_unreadable_rather_than_empty(self):
        """An empty rewrite would erase the message."""
        assert read_outcome({"verdict": "rewritten"}) is None
        assert read_outcome({"verdict": "rewritten", "text": 7}) is None
