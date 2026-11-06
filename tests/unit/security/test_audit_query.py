"""Reading the record of what happened, within what the asker may see."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.audit_query import Asker, Entry, search_audit

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

ENTRIES = (
    Entry(
        event="run-started",
        person="ana",
        team="finance",
        org="acme",
        at=NOW - timedelta(hours=1),
        detail="run r1",
    ),
    Entry(
        event="break-glass-used",
        person="bo",
        team="platform",
        org="acme",
        at=NOW - timedelta(hours=2),
        detail="opened vault",
    ),
    Entry(
        event="run-started",
        person="cy",
        team="legal",
        org="acme",
        at=NOW - timedelta(hours=3),
        detail="run r3",
    ),
    Entry(
        event="run-started",
        person="dee",
        team="finance",
        org="globex",
        at=NOW - timedelta(hours=4),
        detail="run r4",
    ),
)


def asker(**kwargs) -> Asker:
    defaults = {"person": "ana", "team": "finance", "org": "acme", "roles": ()}
    defaults.update(kwargs)
    return Asker(**defaults)


def test_someone_sees_their_own_events():
    found = search_audit(ENTRIES, asker=asker(), now=NOW)
    assert any(entry.person == "ana" for entry in found.entries)


def test_someone_does_not_see_another_teams_events():
    found = search_audit(ENTRIES, asker=asker(), now=NOW)
    assert all(entry.team == "finance" for entry in found.entries)


def test_nobody_sees_another_organisations_events():
    found = search_audit(ENTRIES, asker=asker(), now=NOW)
    assert all(entry.org == "acme" for entry in found.entries)


def test_an_auditor_sees_the_whole_organisation():
    found = search_audit(ENTRIES, asker=asker(roles=("auditor",)), now=NOW)
    assert {entry.team for entry in found.entries} == {"finance", "platform", "legal"}


def test_an_auditor_still_sees_nothing_from_another_organisation():
    found = search_audit(ENTRIES, asker=asker(roles=("auditor",)), now=NOW)
    assert all(entry.org == "acme" for entry in found.entries)


def test_how_many_were_hidden_is_reported():
    found = search_audit(ENTRIES, asker=asker(), now=NOW)
    assert found.hidden == 3


def test_nothing_is_hidden_from_an_auditor_within_the_organisation():
    found = search_audit(ENTRIES, asker=asker(roles=("auditor",)), now=NOW)
    assert found.hidden == 1


def test_events_can_be_narrowed_by_kind():
    found = search_audit(
        ENTRIES, asker=asker(roles=("auditor",)), event="break-glass-used", now=NOW
    )
    assert [entry.person for entry in found.entries] == ["bo"]


def test_events_can_be_narrowed_by_time():
    found = search_audit(
        ENTRIES,
        asker=asker(roles=("auditor",)),
        since=NOW - timedelta(hours=2),
        now=NOW,
    )
    assert len(found.entries) == 2


def test_events_come_back_newest_first():
    found = search_audit(ENTRIES, asker=asker(roles=("auditor",)), now=NOW)
    assert found.entries[0].person == "ana"


def test_the_detail_of_someone_elses_event_is_not_shown():
    found = search_audit(ENTRIES, asker=asker(roles=("auditor",)), now=NOW)
    other = next(entry for entry in found.entries if entry.person == "bo")
    assert other.detail == ""


def test_the_detail_of_your_own_event_is_shown():
    found = search_audit(ENTRIES, asker=asker(roles=("auditor",)), now=NOW)
    mine = next(entry for entry in found.entries if entry.person == "ana")
    assert mine.detail == "run r1"


def test_an_investigator_sees_the_detail_of_other_events():
    found = search_audit(ENTRIES, asker=asker(roles=("investigator",)), now=NOW)
    other = next(entry for entry in found.entries if entry.person == "bo")
    assert other.detail == "opened vault"


def test_a_search_that_finds_nothing_says_so():
    found = search_audit(ENTRIES, asker=asker(), event="never-happened", now=NOW)
    assert found.entries == () and found.reason != ""


def test_asking_about_a_future_window_is_refused():
    with pytest.raises(ValueError):
        search_audit(ENTRIES, asker=asker(), since=NOW + timedelta(days=1), now=NOW)


def test_an_asker_without_an_organisation_is_refused():
    with pytest.raises(ValueError):
        asker(org=" ")
