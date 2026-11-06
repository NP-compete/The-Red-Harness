"""How long a thread is kept before it is thrown away."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.retention import (
    Action,
    RetentionRules,
    Thread,
    decide_retention,
)

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

RULES = RetentionRules(
    keep_days=90,
    archive_after_days=30,
    keep_days_by_classification={"confidential": 30},
)


def thread(**kwargs) -> Thread:
    defaults = {
        "last_activity": NOW - timedelta(days=1),
        "classification": "internal",
        "on_legal_hold": False,
        "pinned": False,
    }
    defaults.update(kwargs)
    return Thread(**defaults)


def test_a_recent_thread_is_left_alone():
    assert decide_retention(thread(), RULES, now=NOW).action is Action.KEEP


def test_a_quiet_thread_is_archived():
    quiet = thread(last_activity=NOW - timedelta(days=45))
    assert decide_retention(quiet, RULES, now=NOW).action is Action.ARCHIVE


def test_an_old_thread_is_deleted():
    old = thread(last_activity=NOW - timedelta(days=120))
    assert decide_retention(old, RULES, now=NOW).action is Action.DELETE


def test_a_stricter_classification_is_deleted_sooner():
    old = thread(last_activity=NOW - timedelta(days=45), classification="confidential")
    assert decide_retention(old, RULES, now=NOW).action is Action.DELETE


def test_a_classification_without_its_own_rule_falls_back_to_the_default():
    old = thread(last_activity=NOW - timedelta(days=45), classification="public")
    assert decide_retention(old, RULES, now=NOW).action is Action.ARCHIVE


def test_a_thread_on_legal_hold_is_never_deleted():
    old = thread(last_activity=NOW - timedelta(days=400), on_legal_hold=True)
    assert decide_retention(old, RULES, now=NOW).action is Action.KEEP


def test_a_legal_hold_says_why_the_thread_survived():
    old = thread(last_activity=NOW - timedelta(days=400), on_legal_hold=True)
    assert "hold" in decide_retention(old, RULES, now=NOW).reason


def test_a_legal_hold_also_prevents_archiving():
    quiet = thread(last_activity=NOW - timedelta(days=45), on_legal_hold=True)
    assert decide_retention(quiet, RULES, now=NOW).action is Action.KEEP


def test_a_pinned_thread_is_not_deleted():
    old = thread(last_activity=NOW - timedelta(days=400), pinned=True)
    assert decide_retention(old, RULES, now=NOW).action is Action.KEEP


def test_a_pinned_thread_may_still_be_archived():
    quiet = thread(last_activity=NOW - timedelta(days=45), pinned=True)
    assert decide_retention(quiet, RULES, now=NOW).action is Action.ARCHIVE


def test_the_decision_says_when_the_thread_will_be_deleted():
    expected = NOW - timedelta(days=1) + timedelta(days=90)
    assert decide_retention(thread(), RULES, now=NOW).delete_on == expected


def test_a_held_thread_has_no_deletion_date():
    held = thread(on_legal_hold=True)
    assert decide_retention(held, RULES, now=NOW).delete_on is None


def test_deletion_is_announced_before_it_happens():
    nearly = thread(last_activity=NOW - timedelta(days=85))
    assert decide_retention(nearly, RULES, now=NOW).warn is True


def test_a_thread_with_time_left_is_not_warned_about():
    assert decide_retention(thread(), RULES, now=NOW).warn is False


def test_archiving_without_a_deletion_rule_keeps_the_thread_for_ever():
    forever = RetentionRules(keep_days=0, archive_after_days=30)
    old = thread(last_activity=NOW - timedelta(days=400))
    decision = decide_retention(old, forever, now=NOW)
    assert decision.action is Action.ARCHIVE
    assert decision.delete_on is None


def test_rules_that_delete_before_they_archive_are_refused():
    with pytest.raises(ValueError):
        RetentionRules(keep_days=10, archive_after_days=30)


@pytest.mark.parametrize("days", [-1, -90])
def test_a_negative_retention_is_refused(days):
    with pytest.raises(ValueError):
        RetentionRules(keep_days=days, archive_after_days=0)
