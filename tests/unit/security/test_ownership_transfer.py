"""Handing a thread to a new owner."""

from __future__ import annotations

import pytest

from agent.src.security.ownership_transfer import Thread, Transfer, plan_transfer


def thread(**kwargs) -> Thread:
    defaults = {
        "thread": "t1",
        "owner": "ada",
        "org": "northwind",
        "readers": ("ada", "grace"),
        "guests": (),
        "under_legal_hold": False,
        "contains_personal_data": False,
    }
    defaults.update(kwargs)
    return Thread(**defaults)


def transfer(**kwargs) -> Transfer:
    defaults = {
        "to": "grace",
        "to_org": "northwind",
        "asked_by": "ada",
        "accepted": True,
    }
    defaults.update(kwargs)
    return Transfer(**defaults)


def test_an_owner_may_hand_over_their_thread():
    assert plan_transfer(thread(), transfer=transfer()).allowed is True


def test_someone_who_does_not_own_it_may_not_hand_it_over():
    assert plan_transfer(thread(), transfer=transfer(asked_by="grace")).allowed is False


def test_a_transfer_out_of_the_organisation_is_refused():
    out = transfer(to_org="eastwind")
    assert plan_transfer(thread(), transfer=out).allowed is False


def test_a_transfer_the_new_owner_has_not_accepted_does_not_happen_yet():
    assert plan_transfer(thread(), transfer=transfer(accepted=False)).allowed is False


def test_an_unaccepted_transfer_is_waiting_rather_than_refused():
    assert plan_transfer(thread(), transfer=transfer(accepted=False)).waiting is True


def test_a_refused_transfer_is_not_waiting():
    assert (
        plan_transfer(thread(), transfer=transfer(to_org="eastwind")).waiting is False
    )


def test_a_thread_under_legal_hold_cannot_change_hands():
    held = thread(under_legal_hold=True)
    assert plan_transfer(held, transfer=transfer()).allowed is False


def test_the_new_owner_is_given_access_if_they_did_not_have_it():
    newcomer = transfer(to="kai")
    assert plan_transfer(thread(), transfer=newcomer).gains_access == ["kai"]


def test_a_new_owner_who_could_already_read_it_gains_nothing():
    assert plan_transfer(thread(), transfer=transfer()).gains_access == []


def test_the_old_owner_keeps_reading_unless_asked_otherwise():
    assert "ada" in plan_transfer(thread(), transfer=transfer()).readers_after


def test_the_new_owner_is_among_the_readers_afterwards():
    newcomer = transfer(to="kai")
    assert "kai" in plan_transfer(thread(), transfer=newcomer).readers_after


def test_guests_do_not_follow_a_thread_to_its_new_owner():
    with_guests = thread(guests=("kai@outside.example",))
    assert plan_transfer(with_guests, transfer=transfer()).guests_dropped == [
        "kai@outside.example"
    ]


def test_a_thread_with_no_guests_drops_nobody():
    assert plan_transfer(thread(), transfer=transfer()).guests_dropped == []


def test_handing_over_personal_data_is_worth_recording():
    personal = thread(contains_personal_data=True)
    assert plan_transfer(personal, transfer=transfer()).audit_note


def test_an_ordinary_transfer_still_says_who_gave_it_to_whom():
    assert (
        plan_transfer(thread(), transfer=transfer()).audit_note
        == "ada handed t1 to grace"
    )


def test_a_refusal_says_why():
    assert plan_transfer(thread(), transfer=transfer(asked_by="grace")).reason


def test_handing_a_thread_to_its_current_owner_is_refused():
    with pytest.raises(ValueError):
        plan_transfer(thread(), transfer=transfer(to="ada"))
