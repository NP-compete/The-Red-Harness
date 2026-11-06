"""Who to ask when a run cannot go on by itself."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.escalation import Ladder, Step, escalate

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)

LADDER = Ladder(
    steps=(
        Step(contact="ana", wait=timedelta(minutes=10)),
        Step(contact="team:platform", wait=timedelta(minutes=30)),
        Step(contact="on-call", wait=timedelta(hours=1)),
    ),
    give_up_after=timedelta(hours=4),
)


def test_the_first_contact_is_asked_first():
    assert escalate(LADDER, asked_at=None, now=NOW).contact == "ana"


def test_nobody_is_asked_twice_before_their_wait_is_up():
    asked = NOW - timedelta(minutes=5)
    assert escalate(LADDER, asked_at=asked, step_index=0, now=NOW).contact == ""


def test_waiting_is_reported_as_waiting_not_as_failure():
    asked = NOW - timedelta(minutes=5)
    assert escalate(LADDER, asked_at=asked, step_index=0, now=NOW).waiting is True


def test_the_wait_remaining_is_reported():
    asked = NOW - timedelta(minutes=5)
    result = escalate(LADDER, asked_at=asked, step_index=0, now=NOW)
    assert result.next_at == asked + timedelta(minutes=10)


def test_the_next_contact_is_asked_once_the_wait_passes():
    asked = NOW - timedelta(minutes=11)
    assert (
        escalate(LADDER, asked_at=asked, step_index=0, now=NOW).contact
        == "team:platform"
    )


def test_escalating_moves_the_step_on():
    asked = NOW - timedelta(minutes=11)
    assert escalate(LADDER, asked_at=asked, step_index=0, now=NOW).step_index == 1


def test_each_step_has_its_own_wait():
    asked = NOW - timedelta(minutes=11)
    result = escalate(LADDER, asked_at=asked, step_index=1, now=NOW)
    assert result.contact == ""


def test_the_last_contact_is_not_escalated_past():
    asked = NOW - timedelta(hours=2)
    result = escalate(LADDER, asked_at=asked, step_index=2, now=NOW)
    assert result.contact == "on-call"


def test_the_last_contact_is_asked_again_rather_than_silently_dropped():
    asked = NOW - timedelta(hours=2)
    assert escalate(LADDER, asked_at=asked, step_index=2, now=NOW).repeated is True


def test_a_run_waiting_too_long_gives_up():
    started = NOW - timedelta(hours=5)
    result = escalate(
        LADDER, asked_at=started, step_index=2, now=NOW, started_at=started
    )
    assert result.gave_up is True


def test_giving_up_asks_nobody_else():
    started = NOW - timedelta(hours=5)
    result = escalate(
        LADDER, asked_at=started, step_index=2, now=NOW, started_at=started
    )
    assert result.contact == ""


def test_giving_up_says_how_long_was_spent_waiting():
    started = NOW - timedelta(hours=5)
    result = escalate(
        LADDER, asked_at=started, step_index=2, now=NOW, started_at=started
    )
    assert "5" in result.reason


def test_giving_up_is_not_an_approval():
    started = NOW - timedelta(hours=5)
    result = escalate(
        LADDER, asked_at=started, step_index=2, now=NOW, started_at=started
    )
    assert result.approved is False


def test_a_ladder_with_no_steps_is_refused():
    with pytest.raises(ValueError):
        Ladder(steps=(), give_up_after=timedelta(hours=1))


def test_a_step_with_no_contact_is_refused():
    with pytest.raises(ValueError):
        Step(contact="  ", wait=timedelta(minutes=1))


def test_a_step_with_no_wait_is_refused():
    with pytest.raises(ValueError):
        Step(contact="ana", wait=timedelta(0))


def test_a_ladder_that_gives_up_before_its_first_wait_is_refused():
    with pytest.raises(ValueError):
        Ladder(
            steps=(Step(contact="ana", wait=timedelta(hours=2)),),
            give_up_after=timedelta(hours=1),
        )
