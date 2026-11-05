"""Tightening what the platform will do while something is wrong."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.incident_mode import Incident, Level, Posture, posture_for

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def incident(**kwargs) -> Incident:
    defaults = {
        "level": Level.DEGRADED,
        "declared_at": NOW - timedelta(minutes=30),
        "declared_by": "on-call",
        "expires_at": NOW + timedelta(hours=2),
        "reason": "elevated failures in the mail tool",
    }
    defaults.update(kwargs)
    return Incident(**defaults)


def test_with_no_incident_everything_runs_normally():
    assert posture_for(None, now=NOW) == Posture.normal()


def test_normal_posture_allows_unattended_runs():
    assert posture_for(None, now=NOW).unattended_runs is True


def test_a_degraded_incident_stops_unattended_runs():
    assert posture_for(incident(), now=NOW).unattended_runs is False


def test_a_degraded_incident_still_allows_people_to_work():
    assert posture_for(incident(), now=NOW).interactive_runs is True


def test_a_degraded_incident_forces_approval_on_risky_steps():
    assert posture_for(incident(), now=NOW).approve_everything_risky is True


def test_a_degraded_incident_lowers_how_much_runs_at_once():
    assert posture_for(incident(), now=NOW).concurrency_factor == 0.5


def test_a_severe_incident_stops_interactive_runs_too():
    assert posture_for(incident(level=Level.SEVERE), now=NOW).interactive_runs is False


def test_a_severe_incident_still_lets_someone_read_what_happened():
    assert posture_for(incident(level=Level.SEVERE), now=NOW).reads is True


def test_reads_are_never_stopped_by_an_incident():
    for level in Level:
        assert posture_for(incident(level=level), now=NOW).reads is True


def test_an_expired_incident_no_longer_applies():
    stale = incident(expires_at=NOW - timedelta(minutes=1))
    assert posture_for(stale, now=NOW) == Posture.normal()


def test_an_incident_carries_its_reason_into_the_posture():
    assert "mail tool" in posture_for(incident(), now=NOW).reason


def test_a_posture_says_who_declared_the_incident():
    assert posture_for(incident(), now=NOW).declared_by == "on-call"


def test_normal_posture_names_nobody():
    assert posture_for(None, now=NOW).declared_by == ""


def test_a_posture_says_when_it_will_lift():
    assert posture_for(incident(), now=NOW).until == NOW + timedelta(hours=2)


def test_an_incident_with_no_end_is_refused():
    with pytest.raises(ValueError):
        Incident(
            level=Level.DEGRADED,
            declared_at=NOW,
            expires_at=NOW,
            declared_by="on-call",
            reason="x",
        )


def test_an_incident_nobody_declared_is_refused():
    with pytest.raises(ValueError):
        incident(declared_by=" ")


def test_an_incident_without_a_reason_is_refused():
    with pytest.raises(ValueError):
        incident(reason="  ")
