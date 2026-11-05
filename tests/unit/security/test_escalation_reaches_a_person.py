"""Turning the decision into a question somebody actually sees."""

from __future__ import annotations

import pytest

from agent.src.security.untrusted_reads import (
    forget_reads,
    needs_a_question_here,
    note_untrusted_read,
)


@pytest.fixture(autouse=True)
def _clean():
    forget_reads()
    yield
    forget_reads()


class TestWhenTheWrapperShouldAsk:
    def test_a_permitted_write_after_a_read(self):
        note_untrusted_read("deploy is blocked on the migration")
        assert needs_a_question_here(
            "post_comment", {"b": "x"}, writes=True, policy="allow"
        )

    def test_a_tool_that_does_not_say_whether_it_writes(self):
        note_untrusted_read("deploy is blocked on the migration")
        assert needs_a_question_here(
            "do_something", {"b": "x"}, writes=None, policy="allow"
        )


class TestWhenItShouldNot:
    def test_nothing_was_read(self):
        assert (
            needs_a_question_here(
                "post_comment", {"b": "x"}, writes=True, policy="allow"
            )
            is None
        )

    def test_the_tool_only_reads(self):
        note_untrusted_read("deploy is blocked on the migration")
        assert (
            needs_a_question_here("get_issue", {"b": "x"}, writes=False, policy="allow")
            is None
        )

    def test_the_policy_already_asks(self):
        note_untrusted_read("deploy is blocked on the migration")
        assert (
            needs_a_question_here("post_comment", {"b": "x"}, writes=True, policy="ask")
            is None
        )

    def test_the_policy_already_refuses(self):
        note_untrusted_read("deploy is blocked on the migration")
        assert (
            needs_a_question_here(
                "post_comment", {"b": "x"}, writes=True, policy="deny"
            )
            is None
        )


class TestTheQuestionSomebodySees:
    @staticmethod
    def _payload():
        from agent.src.security.untrusted_reads import question_payload

        note_untrusted_read("deploy is blocked on the migration")
        return question_payload(
            "post_comment",
            {"body": "Per the ticket: deploy is blocked on the migration"},
            reason="post_comment changes something",
        )

    def test_it_names_the_action(self):
        found = self._payload()
        assert found["action_requests"][0]["name"] == "post_comment"

    def test_it_carries_the_arguments_so_they_can_be_read(self):
        found = self._payload()
        assert found["action_requests"][0]["args"]["body"]

    def test_it_explains_why_it_is_being_asked(self):
        found = self._payload()
        assert "changes something" in found["action_requests"][0]["description"]

    def test_it_offers_a_way_to_say_no(self):
        decisions = self._payload()["review_configs"][0]["allowed_decisions"]
        assert "reject" in decisions

    def test_it_offers_a_way_to_say_yes(self):
        decisions = self._payload()["review_configs"][0]["allowed_decisions"]
        assert "approve" in decisions

    def test_the_action_names_match_between_the_two_halves(self):
        found = self._payload()
        assert (
            found["review_configs"][0]["action_name"]
            == found["action_requests"][0]["name"]
        )


class TestTheWrapperUsesIt:
    def test_the_tool_wrapper_asks_before_a_write(self):
        import inspect

        from agent.aegra import mcp_tool_auth

        source = inspect.getsource(mcp_tool_auth)
        assert "needs_a_question_here" in source


class TestInsideASubagent:
    """A subagent is not a conversation, so it cannot ask."""

    @staticmethod
    def _attempt(nested):
        from unittest.mock import patch

        from agent.aegra import mcp_tool_auth

        note_untrusted_read("deploy is blocked on the migration")
        paused: list = []

        class _Tool:
            name = "post_comment"
            metadata = {"annotations": {"readOnlyHint": False}}

        with (
            patch.object(mcp_tool_auth, "_in_nested_graph", return_value=nested),
            patch.object(
                mcp_tool_auth, "interrupt", side_effect=lambda p: paused.append(p)
            ),
            patch.object(mcp_tool_auth, "_policy_for", return_value="allow"),
        ):
            refused = mcp_tool_auth._ask_if_this_follows_an_untrusted_read(
                _Tool(), {"args": {"body": "x"}}
            )
        return paused, refused

    def test_a_conversation_is_paused(self):
        paused, refused = self._attempt(nested=False)
        assert paused and refused is None

    def test_a_subagent_is_not_paused(self):
        paused, _refused = self._attempt(nested=True)
        assert paused == []

    def test_a_subagent_gets_something_to_report(self):
        _paused, refused = self._attempt(nested=True)
        assert refused and "post_comment" in refused

    def test_what_it_reports_says_why(self):
        _paused, refused = self._attempt(nested=True)
        assert "outside" in refused.lower() or "untrusted" in refused.lower()
