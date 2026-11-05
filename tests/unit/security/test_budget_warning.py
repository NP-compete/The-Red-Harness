"""Telling somebody they are running out before they run out."""

from __future__ import annotations

import pytest

from agent.src.security.budget_warning import Level, assess


def test_plenty_left_says_nothing():
    assert assess(used=10, limit=100).level is Level.FINE


def test_approaching_the_limit_warns():
    assert assess(used=80, limit=100).level is Level.WARNING


def test_at_the_limit_is_spent():
    assert assess(used=100, limit=100).level is Level.SPENT


def test_over_the_limit_is_still_spent_rather_than_negative():
    assessment = assess(used=150, limit=100)
    assert assessment.level is Level.SPENT
    assert assessment.remaining == 0


def test_no_limit_means_nothing_to_warn_about():
    assert assess(used=10_000, limit=None).level is Level.FINE


def test_a_warning_says_how_much_is_left():
    assert assess(used=80, limit=100).remaining == 20


def test_a_warning_is_phrased_for_a_person():
    message = assess(used=80, limit=100).message
    assert "20" in message and "%" in message


def test_being_spent_says_what_to_do_next():
    assert "new" in assess(used=100, limit=100).message.lower()


def test_being_fine_says_nothing_at_all():
    assert assess(used=1, limit=100).message == ""


def test_the_warning_point_can_be_moved():
    assert assess(used=50, limit=100, warn_at=0.5).level is Level.WARNING


@pytest.mark.parametrize("limit", [0, -1])
def test_a_nonsense_limit_is_refused(limit):
    with pytest.raises(ValueError):
        assess(used=1, limit=limit)
