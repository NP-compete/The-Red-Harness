"""Keeping conversations that a deletion would otherwise remove."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.legal_hold import Hold, Holds

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def holds(*entries: Hold) -> Holds:
    return Holds(list(entries), now=lambda: NOW)


def hold(**kwargs) -> Hold:
    defaults = {
        "reference": "case-1",
        "subjects": ("me@example.com",),
        "placed_by": "legal@example.com",
        "lifted_at": None,
    }
    defaults.update(kwargs)
    return Hold(**defaults)


def test_nothing_is_held_by_default():
    assert holds().covers("me@example.com") is False


def test_a_person_under_hold_is_covered():
    assert holds(hold()).covers("me@example.com") is True


def test_somebody_not_named_is_not_covered():
    assert holds(hold()).covers("other@example.com") is False


def test_a_lifted_hold_no_longer_covers():
    lifted = hold(lifted_at=NOW - timedelta(days=1))
    assert holds(lifted).covers("me@example.com") is False


def test_a_hold_lifted_in_the_future_still_covers():
    future = hold(lifted_at=NOW + timedelta(days=1))
    assert holds(future).covers("me@example.com") is True


def test_several_holds_can_cover_one_person():
    two = holds(hold(reference="case-1"), hold(reference="case-2"))
    assert two.references("me@example.com") == ("case-1", "case-2")


def test_lifting_one_of_two_holds_still_covers():
    two = holds(
        hold(reference="case-1", lifted_at=NOW - timedelta(days=1)),
        hold(reference="case-2"),
    )
    assert two.covers("me@example.com") is True


def test_a_deletion_under_hold_is_refused():
    with pytest.raises(PermissionError):
        holds(hold()).check_deletion("me@example.com")


def test_a_deletion_not_under_hold_proceeds():
    holds(hold()).check_deletion("other@example.com")


def test_the_refusal_names_the_hold_so_it_can_be_chased():
    with pytest.raises(PermissionError, match="case-1"):
        holds(hold()).check_deletion("me@example.com")


def test_a_hold_must_say_who_placed_it():
    with pytest.raises(ValueError):
        Hold(
            reference="case-1",
            subjects=("me@example.com",),
            placed_by="  ",
            lifted_at=None,
        )


def test_a_hold_must_name_somebody():
    with pytest.raises(ValueError):
        Hold(
            reference="case-1",
            subjects=(),
            placed_by="legal@example.com",
            lifted_at=None,
        )
