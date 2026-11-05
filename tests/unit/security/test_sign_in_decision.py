"""Whether someone gets in, and what they have to prove first."""

from __future__ import annotations

import pytest

from agent.src.security.sign_in_decision import Attempt, Outcome, decide_sign_in


def attempt(**kwargs) -> Attempt:
    defaults = {
        "person": "ana",
        "network_allowed": True,
        "network_exceptional": False,
        "device_known": True,
        "device_step_up": False,
        "new_location": False,
        "has_seat": True,
        "account_active": True,
    }
    defaults.update(kwargs)
    return Attempt(**defaults)


def test_an_ordinary_sign_in_is_allowed():
    assert decide_sign_in(attempt()).outcome is Outcome.ALLOWED


def test_an_ordinary_sign_in_needs_nothing_extra():
    assert decide_sign_in(attempt()).step_up is False


def test_a_closed_account_is_refused():
    assert decide_sign_in(attempt(account_active=False)).outcome is Outcome.REFUSED


def test_a_closed_account_outranks_everything_else():
    closed = attempt(account_active=False, network_allowed=False, device_known=False)
    assert "account" in decide_sign_in(closed).reason


def test_an_unpermitted_network_is_refused():
    assert decide_sign_in(attempt(network_allowed=False)).outcome is Outcome.REFUSED


def test_a_refused_network_does_not_say_which_networks_are_allowed():
    decision = decide_sign_in(attempt(network_allowed=False))
    assert "allowed" not in decision.reason


def test_a_new_device_asks_for_more_proof():
    assert decide_sign_in(attempt(device_known=False)).outcome is Outcome.STEP_UP


def test_a_new_location_asks_for_more_proof():
    assert decide_sign_in(attempt(new_location=True)).outcome is Outcome.STEP_UP


def test_an_untrusted_known_device_asks_for_more_proof():
    assert decide_sign_in(attempt(device_step_up=True)).outcome is Outcome.STEP_UP


def test_someone_without_a_seat_gets_in_but_can_do_nothing():
    decision = decide_sign_in(attempt(has_seat=False))
    assert decision.outcome is Outcome.ALLOWED and decision.read_only is True


def test_someone_with_a_seat_is_not_read_only():
    assert decide_sign_in(attempt()).read_only is False


def test_a_sign_in_needing_proof_is_not_yet_read_only():
    assert decide_sign_in(attempt(device_known=False)).read_only is False


def test_an_exceptional_network_is_allowed_but_recorded():
    decision = decide_sign_in(attempt(network_exceptional=True))
    assert decision.outcome is Outcome.ALLOWED and decision.exceptional is True


def test_an_exceptional_network_still_asks_for_proof_on_a_new_device():
    both = attempt(network_exceptional=True, device_known=False)
    assert decide_sign_in(both).outcome is Outcome.STEP_UP


def test_an_ordinary_sign_in_is_not_exceptional():
    assert decide_sign_in(attempt()).exceptional is False


def test_whether_to_tell_the_person_is_reported():
    assert decide_sign_in(attempt(device_known=False)).notify is True


def test_an_ordinary_sign_in_needs_no_notification():
    assert decide_sign_in(attempt()).notify is False


def test_a_sign_in_without_a_person_is_refused():
    with pytest.raises(ValueError):
        attempt(person="  ")
