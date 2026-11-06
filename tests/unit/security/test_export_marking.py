"""Marking exported content so it can be traced back."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agent.src.security.export_marking import Export, Placement, mark_export

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def export(**kwargs) -> Export:
    defaults = {
        "content": "The expense limit is 500.",
        "format": "markdown",
        "person": "ana",
        "org": "acme",
        "classification": "internal",
    }
    defaults.update(kwargs)
    return Export(**defaults)


def test_the_original_content_is_kept():
    assert "The expense limit is 500." in mark_export(export(), now=NOW).content


def test_a_mark_is_added():
    assert mark_export(export(), now=NOW).marked is True


def test_the_mark_names_the_organisation():
    assert "acme" in mark_export(export(), now=NOW).content


def test_the_mark_carries_the_date():
    assert "2026-10-27" in mark_export(export(), now=NOW).content


def test_the_mark_does_not_name_the_person_in_the_content():
    assert "ana" not in mark_export(export(), now=NOW).content


def test_who_exported_it_is_recorded_separately():
    assert mark_export(export(), now=NOW).exported_by == "ana"


def test_an_identifier_links_the_copy_to_the_record():
    marked = mark_export(export(), now=NOW)
    assert marked.export_id and marked.export_id in marked.content


def test_the_same_export_twice_gets_different_identifiers():
    first = mark_export(export(), now=NOW)
    second = mark_export(export(), now=NOW)
    assert first.export_id != second.export_id


def test_a_markdown_export_is_marked_at_the_end():
    assert mark_export(export(), now=NOW).placement is Placement.FOOTER


def test_a_markdown_mark_is_a_comment_rather_than_a_heading():
    assert (
        mark_export(export(format="markdown"), now=NOW).content.rstrip().endswith("-->")
    )


def test_a_plain_text_export_is_marked_at_the_end_too():
    marked = mark_export(export(format="text"), now=NOW)
    assert marked.content.rstrip().endswith(marked.export_id)


def test_a_json_export_is_not_marked_inside_the_content():
    marked = mark_export(export(format="json", content='{"limit": 500}'), now=NOW)
    assert marked.content == '{"limit": 500}'


def test_a_json_export_says_it_could_not_be_marked():
    marked = mark_export(export(format="json", content='{"limit": 500}'), now=NOW)
    assert marked.marked is False and marked.placement is Placement.NONE


def test_a_json_export_is_still_recorded():
    marked = mark_export(export(format="json", content='{"limit": 500}'), now=NOW)
    assert marked.export_id != ""


def test_a_confidential_export_says_so_in_the_mark():
    marked = mark_export(export(classification="confidential"), now=NOW)
    assert "confidential" in marked.content


def test_a_public_export_is_not_marked_at_all():
    marked = mark_export(export(classification="public"), now=NOW)
    assert marked.marked is False


def test_empty_content_is_refused():
    with pytest.raises(ValueError):
        export(content="   ")


def test_an_unknown_format_is_refused():
    with pytest.raises(ValueError):
        export(format="hieroglyphs")
