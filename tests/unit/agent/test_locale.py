"""Choosing the language, zone and units a reply is written in."""

from __future__ import annotations

import pytest

from agent.src.agent.locale import Signals, choose_locale


def signals(**kwargs) -> Signals:
    defaults = {
        "chosen_language": "",
        "chosen_zone": "",
        "chosen_units": "",
        "language_written_in": "en",
        "workspace_language": "en",
        "workspace_zone": "UTC",
        "workspace_units": "metric",
        "device_zone": "",
    }
    defaults.update(kwargs)
    return Signals(**defaults)


def test_the_workspace_language_is_the_starting_point():
    assert choose_locale(signals()).language == "en"


def test_a_setting_the_person_chose_wins():
    assert choose_locale(signals(chosen_language="de")).language == "de"


def test_the_language_they_wrote_in_beats_the_workspace_default():
    assert choose_locale(signals(language_written_in="fr")).language == "fr"


def test_a_chosen_language_beats_the_language_they_wrote_in():
    picked = signals(chosen_language="de", language_written_in="fr")
    assert choose_locale(picked).language == "de"


def test_the_workspace_zone_is_used_when_nothing_else_is_known():
    assert (
        choose_locale(signals(workspace_zone="Europe/Berlin")).zone == "Europe/Berlin"
    )


def test_the_device_zone_beats_the_workspace_zone():
    travelling = signals(workspace_zone="Europe/Berlin", device_zone="Asia/Tokyo")
    assert choose_locale(travelling).zone == "Asia/Tokyo"


def test_a_chosen_zone_beats_the_device():
    pinned = signals(chosen_zone="Europe/Berlin", device_zone="Asia/Tokyo")
    assert choose_locale(pinned).zone == "Europe/Berlin"


def test_units_follow_the_workspace_unless_chosen():
    assert choose_locale(signals(workspace_units="imperial")).units == "imperial"


def test_a_chosen_unit_system_wins():
    picked = signals(chosen_units="metric", workspace_units="imperial")
    assert choose_locale(picked).units == "metric"


def test_units_are_not_guessed_from_the_language():
    assert choose_locale(signals(language_written_in="fr")).units == "metric"


def test_the_reason_for_the_language_is_reported():
    assert choose_locale(signals(language_written_in="fr")).language_from == "message"


def test_a_chosen_language_is_reported_as_chosen():
    assert choose_locale(signals(chosen_language="de")).language_from == "setting"


def test_a_default_language_is_reported_as_the_workspace_s():
    assert choose_locale(signals()).language_from == "workspace"


def test_it_is_worth_mentioning_when_the_reply_switches_language():
    switched = signals(workspace_language="en", language_written_in="fr")
    assert choose_locale(switched).switched is True


def test_no_mention_is_needed_when_nothing_switched():
    assert choose_locale(signals()).switched is False


def test_an_unknown_zone_falls_back_rather_than_failing():
    assert choose_locale(signals(device_zone="Mars/Olympus")).zone == "UTC"


def test_a_workspace_with_no_language_is_refused():
    with pytest.raises(ValueError):
        signals(workspace_language="")
