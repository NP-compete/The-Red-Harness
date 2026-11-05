"""Removing somebody's data, without taking anybody else's with it."""

from __future__ import annotations

import pytest

from agent.src.security.data_deletion import plan_deletion

HELD = {
    "conversations": [
        {"id": "t1", "owner": "me@example.com"},
        {"id": "t2", "owner": "other@example.com"},
    ],
    "memory": [{"id": "m1", "owner": "me@example.com"}],
    "documents": [
        {"id": "d1", "owner": "me@example.com", "scope": "user"},
        {"id": "d2", "owner": "me@example.com", "scope": "team"},
    ],
    "audit": [{"id": "a1", "subject": "me@example.com"}],
}


def plan(**kwargs):
    defaults = {"subject": "me@example.com", "held": HELD}
    defaults.update(kwargs)
    return plan_deletion(**defaults)


def test_their_own_records_are_removed():
    assert "t1" in plan().delete["conversations"]


def test_somebody_else_records_are_left_alone():
    assert "t2" not in plan().delete["conversations"]


def test_team_content_is_kept_rather_than_deleted():
    assert "d2" not in plan().delete["documents"]


def test_team_content_is_reported_as_kept():
    assert "d2" in plan().kept["documents"]


def test_private_documents_are_deleted():
    assert "d1" in plan().delete["documents"]


def test_the_audit_trail_is_never_deleted():
    assert "audit" not in plan().delete


def test_the_audit_trail_is_reported_as_retained():
    assert "a1" in plan().retained["audit"]


def test_the_reason_the_audit_trail_stays_is_given():
    assert "audit" in plan().notes[0].lower()


def test_nothing_is_deleted_by_planning():
    planned = plan()
    assert HELD["conversations"][0]["id"] == "t1"
    assert planned.delete["conversations"] == ["t1"]


def test_a_person_with_nothing_plans_cleanly():
    planned = plan(subject="nobody@example.com")
    assert all(ids == [] for ids in planned.delete.values())


def test_how_much_will_go_is_counted():
    assert plan().counts["conversations"] == 1


@pytest.mark.parametrize("subject", ["", "  "])
def test_a_deletion_needs_somebody_to_be_for(subject):
    with pytest.raises(ValueError):
        plan(subject=subject)
