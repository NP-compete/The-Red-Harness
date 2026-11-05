"""A write that follows an untrusted read should be asked about."""

from __future__ import annotations

import pytest

from agent.src.security.untrusted_reads import (
    forget_reads,
    note_untrusted_read,
    read_something_untrusted,
    why_ask_before,
)


@pytest.fixture(autouse=True)
def _clean():
    forget_reads()
    yield
    forget_reads()


class TestTheRunRemembersAReadHappened:
    def test_a_fresh_run_has_read_nothing(self):
        assert read_something_untrusted() is False

    def test_a_read_is_remembered(self):
        note_untrusted_read("a ticket said something")
        assert read_something_untrusted() is True

    def test_a_new_run_starts_clean(self):
        note_untrusted_read("a ticket said something")
        forget_reads()
        assert read_something_untrusted() is False

    def test_empty_text_is_not_a_read(self):
        note_untrusted_read("")
        assert read_something_untrusted() is False


class TestWhenAWriteIsAskedAbout:
    def test_nothing_is_asked_before_any_read(self):
        assert why_ask_before("post_comment", {"body": "hello"}, writes=True) is None

    def test_a_write_after_a_read_is_asked_about(self):
        note_untrusted_read("deploy is blocked on the migration")
        assert why_ask_before("post_comment", {"body": "hello"}, writes=True)

    def test_a_read_only_tool_is_not(self):
        note_untrusted_read("deploy is blocked on the migration")
        assert why_ask_before("get_issue", {"id": "4471"}, writes=False) is None

    def test_a_tool_that_does_not_say_is_treated_as_a_write(self):
        note_untrusted_read("deploy is blocked on the migration")
        assert why_ask_before("do_something", {"x": "1"}, writes=None)


class TestTheReasonIsWorthReading:
    def test_it_names_the_tool(self):
        note_untrusted_read("deploy is blocked on the migration")
        assert "post_comment" in why_ask_before("post_comment", {"b": "x"}, writes=True)

    def test_it_says_the_run_read_something_from_outside(self):
        note_untrusted_read("deploy is blocked on the migration")
        said = why_ask_before("post_comment", {"b": "x"}, writes=True).lower()
        assert "outside" in said or "untrusted" in said or "external" in said

    def test_a_repeated_fragment_is_quoted_back(self):
        note_untrusted_read("deploy is blocked on the migration")
        said = why_ask_before(
            "post_comment",
            {"body": "Per the ticket: deploy is blocked on the migration"},
            writes=True,
        )
        assert "deploy is blocked on the migration" in said

    def test_an_unrelated_write_still_asks_but_quotes_nothing(self):
        note_untrusted_read("deploy is blocked on the migration")
        said = why_ask_before("post_comment", {"body": "unrelated"}, writes=True)
        assert said and "deploy is blocked" not in said


class TestShortFragmentsDoNotMatchEverything:
    def test_a_tiny_read_does_not_get_quoted_into_every_write(self):
        note_untrusted_read("ok")
        said = why_ask_before("post_comment", {"body": "looks ok to me"}, writes=True)
        assert said is None or "ok" not in said.split("read: ")[-1]


class TestItNeverCostsTheTurn:
    def test_arguments_it_cannot_walk_do_not_raise(self):
        note_untrusted_read("deploy is blocked on the migration")
        assert why_ask_before("post_comment", object(), writes=True)

    def test_recording_something_that_is_not_text_does_not_raise(self):
        note_untrusted_read(None)
        assert read_something_untrusted() is False


class TestItIsFedByTheRealPath:
    """Recorded where results actually arrive, forgotten per run."""

    def test_a_fenced_result_is_recorded(self):
        from agent.aegra.mcp_tool_auth import _as_external

        _as_external("jira_get_issue", "deploy is blocked on the migration")
        assert read_something_untrusted() is True

    def test_a_vouched_server_is_not(self):
        from unittest.mock import patch

        from agent.aegra.mcp_tool_auth import _as_external

        with patch("agent.aegra.mcp_tool_auth._is_vouched_for", return_value=True):
            _as_external("ours_get_thing", "deploy is blocked on the migration")
        assert read_something_untrusted() is False

    def test_a_structured_result_is_not_recorded_as_text(self):
        from agent.aegra.mcp_tool_auth import _as_external

        _as_external("jira_get_issue", {"id": 4471})
        assert read_something_untrusted() is False

    def test_something_resets_it_between_runs(self):
        import inspect

        from agent.src.infrastructure import middleware

        assert "forget_reads" in inspect.getsource(middleware)
