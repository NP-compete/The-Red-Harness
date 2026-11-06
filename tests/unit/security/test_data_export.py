"""Giving somebody everything the system holds about them."""

from __future__ import annotations

import pytest

from agent.src.security.data_export import build_export

HELD = {
    "conversations": [{"id": "t1", "messages": ["hello"]}],
    "memory": [{"text": "prefers short answers"}],
    "documents": [{"name": "notes.txt"}],
    "artifacts": [{"key": "checklist"}],
}


def test_everything_held_is_included():
    export = build_export(subject="me@example.com", held=HELD)
    assert set(export.sections) == set(HELD)


def test_the_export_names_who_it_is_for():
    assert build_export(subject="me@example.com", held=HELD).subject == "me@example.com"


def test_an_empty_section_is_still_listed_so_nothing_looks_hidden():
    export = build_export(subject="me@example.com", held={**HELD, "documents": []})
    assert "documents" in export.sections


def test_credentials_are_never_exported():
    held = {**HELD, "credentials": [{"server": "tracker", "token": "sk-live-x"}]}
    export = build_export(subject="me@example.com", held=held)
    assert "sk-live-x" not in str(export.sections)


def test_the_fact_that_credentials_exist_is_still_reported():
    held = {**HELD, "credentials": [{"server": "tracker", "token": "sk-live-x"}]}
    export = build_export(subject="me@example.com", held=held)
    assert export.sections["credentials"] == [{"server": "tracker"}]


def test_somebody_else_data_is_refused_rather_than_filtered():
    held = {**HELD, "conversations": [{"id": "t1", "owner": "other@example.com"}]}
    with pytest.raises(ValueError):
        build_export(subject="me@example.com", held=held)


def test_a_conversation_owned_by_the_subject_is_fine():
    held = {**HELD, "conversations": [{"id": "t1", "owner": "me@example.com"}]}
    assert build_export(subject="me@example.com", held=held).sections["conversations"]


def test_the_export_says_when_it_was_made():
    assert build_export(
        subject="me@example.com", held=HELD, made_at="2026-10-27"
    ).made_at == ("2026-10-27")


def test_counts_are_included_so_the_export_can_be_checked():
    export = build_export(subject="me@example.com", held=HELD)
    assert export.counts["conversations"] == 1


def test_an_export_for_somebody_with_nothing_is_still_valid():
    export = build_export(subject="new@example.com", held={})
    assert export.sections == {}
    assert export.counts == {}


@pytest.mark.parametrize("subject", ["", "   "])
def test_an_export_needs_somebody_to_be_for(subject):
    with pytest.raises(ValueError):
        build_export(subject=subject, held=HELD)
