"""Naming where an answer's words came from."""

from __future__ import annotations

import pytest

from agent.src.security.untrusted_reads import (
    forget_reads,
    note_untrusted_read,
    sources_behind,
)


@pytest.fixture(autouse=True)
def _clean():
    forget_reads()
    yield
    forget_reads()


class TestWhenAnAnswerRepeatsSomething:
    def test_the_source_is_named(self):
        note_untrusted_read("deploy is blocked on the migration", source="jira")
        found = sources_behind("The deploy is blocked on the migration, apparently.")
        assert "jira" in found

    def test_two_sources_are_both_named(self):
        note_untrusted_read("deploy is blocked on the migration", source="jira")
        note_untrusted_read("the runbook says to roll forward", source="wiki")
        found = sources_behind(
            "Deploy is blocked on the migration; the runbook says to roll forward."
        )
        assert set(found) == {"jira", "wiki"}

    def test_a_source_is_named_once_however_often_it_is_quoted(self):
        note_untrusted_read("deploy is blocked on the migration", source="jira")
        note_untrusted_read("owner is sam and the ticket is open", source="jira")
        found = sources_behind(
            "deploy is blocked on the migration. owner is sam and the ticket is open."
        )
        assert found == ("jira",)


class TestWhenItDoesNot:
    def test_an_answer_from_the_model_names_nothing(self):
        note_untrusted_read("deploy is blocked on the migration", source="jira")
        assert sources_behind("Rome was founded in 753 BC.") == ()

    def test_nothing_read_means_nothing_to_name(self):
        assert sources_behind("anything at all") == ()

    def test_an_empty_answer_names_nothing(self):
        note_untrusted_read("deploy is blocked on the migration", source="jira")
        assert sources_behind("") == ()


class TestItDoesNotCryWolf:
    def test_a_short_line_does_not_attribute_every_answer(self):
        note_untrusted_read("ok", source="jira")
        assert sources_behind("That looks ok to me.") == ()

    def test_a_read_with_no_source_is_not_attributed_to_nothing(self):
        note_untrusted_read("deploy is blocked on the migration", source="")
        assert sources_behind("deploy is blocked on the migration") == ()


class TestItNeverCostsTheAnswer:
    def test_something_that_is_not_text_does_not_raise(self):
        note_untrusted_read("deploy is blocked on the migration", source="jira")
        assert sources_behind(None) == ()

    def test_recording_without_a_source_still_arms_the_write_rule(self):
        from agent.src.security.untrusted_reads import read_something_untrusted

        note_untrusted_read("deploy is blocked on the migration", source="")
        assert read_something_untrusted() is True


class TestItIsFedAndWrittenDown:
    def test_the_wrapper_passes_the_server_name(self):
        from agent.aegra.mcp_tool_auth import _as_external

        _as_external("jira_get_issue", "deploy is blocked on the migration")
        assert "jira_get_issue" in sources_behind(
            "The deploy is blocked on the migration."
        )

    def test_the_turn_records_what_the_answer_drew_on(self):
        from agent.src.knowledge.citation_middleware import stamp_citations

        class _Answer:
            content = "Deploy is blocked on the migration, per the ticket."
            additional_kwargs: dict = {}

        note_untrusted_read("deploy is blocked on the migration", source="jira")
        message = _Answer()
        stamp_citations(message, [])

        notes = message.additional_kwargs.get("answer_notes", {})
        assert notes.get("from_outside") == ["jira"]

    def test_an_answer_that_drew_on_nothing_records_nothing(self):
        from agent.src.knowledge.citation_middleware import stamp_citations

        class _Answer:
            content = "Rome was founded in 753 BC."
            additional_kwargs: dict = {}

        note_untrusted_read("deploy is blocked on the migration", source="jira")
        message = _Answer()
        stamp_citations(message, [])
        assert "from_outside" not in message.additional_kwargs.get("answer_notes", {})
