"""Deciding whether to interrupt a person, and when."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

import pytest

from agent.src.security.notification import (
    Event,
    Preferences,
    Urgency,
    When,
    decide_notification,
)

MORNING = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)
NIGHT = datetime(2026, 10, 27, 23, 30, tzinfo=timezone.utc)

PREFERENCES = Preferences(
    quiet_from=time(22, 0),
    quiet_until=time(7, 0),
    muted_kinds=("run-finished",),
    allow_urgent_during_quiet_hours=True,
)


def event(**kwargs) -> Event:
    defaults = {
        "kind": "approval-needed",
        "urgency": Urgency.NORMAL,
        "key": "run-1",
        "last_sent": None,
    }
    defaults.update(kwargs)
    return Event(**defaults)


def test_an_ordinary_event_is_sent_now():
    assert decide_notification(event(), PREFERENCES, now=MORNING).when is When.NOW


def test_a_muted_kind_is_not_sent_at_all():
    muted = event(kind="run-finished")
    assert decide_notification(muted, PREFERENCES, now=MORNING).when is When.NEVER


def test_a_muted_kind_says_it_was_muted():
    muted = event(kind="run-finished")
    assert "muted" in decide_notification(muted, PREFERENCES, now=MORNING).reason


def test_an_event_during_quiet_hours_waits():
    assert decide_notification(event(), PREFERENCES, now=NIGHT).when is When.LATER


def test_a_waiting_event_says_when_it_will_arrive():
    decision = decide_notification(event(), PREFERENCES, now=NIGHT)
    assert decision.send_at == datetime(2026, 10, 28, 7, 0, tzinfo=timezone.utc)


def test_an_urgent_event_breaks_through_quiet_hours():
    urgent = event(urgency=Urgency.URGENT)
    assert decide_notification(urgent, PREFERENCES, now=NIGHT).when is When.NOW


def test_an_urgent_event_is_held_when_that_was_not_allowed():
    strict = Preferences(
        quiet_from=time(22, 0),
        quiet_until=time(7, 0),
        muted_kinds=(),
        allow_urgent_during_quiet_hours=False,
    )
    assert (
        decide_notification(event(urgency=Urgency.URGENT), strict, now=NIGHT).when
        is When.LATER
    )


def test_a_muted_kind_stays_muted_even_when_urgent():
    muted = event(kind="run-finished", urgency=Urgency.URGENT)
    assert decide_notification(muted, PREFERENCES, now=MORNING).when is When.NEVER


def test_the_same_event_is_not_sent_twice_in_quick_succession():
    repeat = event(last_sent=MORNING - timedelta(minutes=2))
    assert decide_notification(repeat, PREFERENCES, now=MORNING).when is When.NEVER


def test_a_suppressed_repeat_says_it_was_already_sent():
    repeat = event(last_sent=MORNING - timedelta(minutes=2))
    assert "already" in decide_notification(repeat, PREFERENCES, now=MORNING).reason


def test_the_same_event_may_be_sent_again_after_long_enough():
    stale = event(last_sent=MORNING - timedelta(hours=2))
    assert decide_notification(stale, PREFERENCES, now=MORNING).when is When.NOW


def test_an_urgent_repeat_is_still_suppressed():
    repeat = event(urgency=Urgency.URGENT, last_sent=MORNING - timedelta(minutes=2))
    assert decide_notification(repeat, PREFERENCES, now=MORNING).when is When.NEVER


def test_quiet_hours_that_do_not_cross_midnight_are_honoured():
    lunch = Preferences(
        quiet_from=time(12, 0),
        quiet_until=time(13, 0),
        muted_kinds=(),
        allow_urgent_during_quiet_hours=False,
    )
    noon = datetime(2026, 10, 27, 12, 30, tzinfo=timezone.utc)
    assert decide_notification(event(), lunch, now=noon).when is When.LATER


def test_an_event_outside_those_hours_is_sent():
    lunch = Preferences(
        quiet_from=time(12, 0),
        quiet_until=time(13, 0),
        muted_kinds=(),
        allow_urgent_during_quiet_hours=False,
    )
    assert decide_notification(event(), lunch, now=MORNING).when is When.NOW


def test_no_quiet_hours_means_no_waiting():
    always = Preferences(
        quiet_from=None,
        quiet_until=None,
        muted_kinds=(),
        allow_urgent_during_quiet_hours=False,
    )
    assert decide_notification(event(), always, now=NIGHT).when is When.NOW


def test_an_event_without_a_key_cannot_be_deduplicated_and_is_refused():
    with pytest.raises(ValueError):
        event(key=" ")


def test_half_specified_quiet_hours_are_refused():
    with pytest.raises(ValueError):
        Preferences(
            quiet_from=time(22, 0),
            quiet_until=None,
            muted_kinds=(),
            allow_urgent_during_quiet_hours=False,
        )
