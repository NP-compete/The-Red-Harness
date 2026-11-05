"""Putting together what support needs without handing over secrets."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.support_bundle import Section, build_bundle

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

SECTIONS = (
    Section(name="versions", content="agent 4.2\nui 3.1", sensitive=False),
    Section(
        name="config", content="model: fast\napi_key: 9f2b7c1e4a6d8035", sensitive=True
    ),
    Section(name="recent-errors", content="TimeoutError at 09:00", sensitive=False),
)


def test_a_bundle_contains_the_ordinary_sections():
    bundle = build_bundle(SECTIONS, now=NOW, requested_by="ana")
    assert "agent 4.2" in bundle.content


def test_a_bundle_says_who_asked_for_it():
    assert build_bundle(SECTIONS, now=NOW, requested_by="ana").requested_by == "ana"


def test_a_bundle_says_when_it_was_made():
    assert build_bundle(SECTIONS, now=NOW, requested_by="ana").created_at == NOW


def test_a_secret_never_reaches_the_bundle():
    bundle = build_bundle(SECTIONS, now=NOW, requested_by="ana")
    assert "9f2b7c1e4a6d8035" not in bundle.content


def test_the_setting_around_a_secret_is_still_visible():
    bundle = build_bundle(SECTIONS, now=NOW, requested_by="ana")
    assert "api_key" in bundle.content


def test_a_removed_secret_leaves_a_visible_gap():
    bundle = build_bundle(SECTIONS, now=NOW, requested_by="ana")
    assert "********" in bundle.content


def test_the_bundle_says_how_many_things_were_removed():
    assert build_bundle(SECTIONS, now=NOW, requested_by="ana").redactions == 1


def test_a_bundle_with_nothing_to_remove_says_so():
    clean = (Section(name="versions", content="agent 4.2", sensitive=False),)
    assert build_bundle(clean, now=NOW, requested_by="ana").redactions == 0


def test_sections_are_listed_so_the_reader_knows_what_is_inside():
    bundle = build_bundle(SECTIONS, now=NOW, requested_by="ana")
    assert bundle.sections == ("versions", "config", "recent-errors")


def test_a_section_can_be_left_out_on_request():
    bundle = build_bundle(SECTIONS, now=NOW, requested_by="ana", exclude=("config",))
    assert "config" not in bundle.sections


def test_leaving_a_section_out_removes_its_content_too():
    bundle = build_bundle(SECTIONS, now=NOW, requested_by="ana", exclude=("config",))
    assert "api_key" not in bundle.content


def test_a_bundle_expires_so_it_does_not_sit_around():
    bundle = build_bundle(SECTIONS, now=NOW, requested_by="ana")
    assert bundle.expires_at == NOW + timedelta(days=7)


def test_an_empty_bundle_is_refused():
    with pytest.raises(ValueError):
        build_bundle((), now=NOW, requested_by="ana")


def test_a_bundle_with_every_section_excluded_is_refused():
    with pytest.raises(ValueError):
        build_bundle(
            SECTIONS,
            now=NOW,
            requested_by="ana",
            exclude=("versions", "config", "recent-errors"),
        )


def test_a_bundle_nobody_asked_for_is_refused():
    with pytest.raises(ValueError):
        build_bundle(SECTIONS, now=NOW, requested_by="  ")


def test_a_section_without_a_name_is_refused():
    with pytest.raises(ValueError):
        Section(name=" ", content="x", sensitive=False)


def test_the_same_input_produces_the_same_bundle():
    first = build_bundle(SECTIONS, now=NOW, requested_by="ana")
    second = build_bundle(SECTIONS, now=NOW, requested_by="ana")
    assert first.content == second.content
