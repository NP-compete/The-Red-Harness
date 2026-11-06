"""Checking who an outgoing message would actually reach."""

from __future__ import annotations

import pytest

from agent.src.security.recipient_check import Recipient, check_recipients


def person(address: str, **kwargs) -> Recipient:
    defaults = {
        "address": address,
        "inside": True,
        "is_list": False,
        "reaches": 1,
        "known": True,
    }
    defaults.update(kwargs)
    return Recipient(**defaults)


def test_one_colleague_needs_no_second_thought():
    assert check_recipients([person("ada@inside.example")]).confirm is False


def test_someone_outside_the_organisation_is_worth_confirming():
    outsider = person("kai@outside.example", inside=False)
    assert check_recipients([outsider]).confirm is True


def test_an_outsider_is_named():
    outsider = person("kai@outside.example", inside=False)
    assert check_recipients([outsider]).outside == ["kai@outside.example"]


def test_a_mailing_list_is_worth_confirming():
    everyone = person("all@inside.example", is_list=True, reaches=400)
    assert check_recipients([everyone]).confirm is True


def test_how_many_people_would_be_reached_is_counted():
    recipients = [
        person("ada@inside.example"),
        person("all@inside.example", is_list=True, reaches=400),
    ]
    assert check_recipients(recipients).reaches == 401


def test_a_small_group_of_colleagues_needs_no_confirming():
    recipients = [person(f"p{i}@inside.example") for i in range(4)]
    assert check_recipients(recipients).confirm is False


def test_a_large_group_of_colleagues_is_worth_confirming():
    recipients = [person(f"p{i}@inside.example") for i in range(30)]
    assert check_recipients(recipients).confirm is True


def test_an_address_never_written_to_before_is_worth_confirming():
    stranger = person("new@inside.example", known=False)
    assert check_recipients([stranger]).confirm is True


def test_an_unfamiliar_address_is_named():
    stranger = person("new@inside.example", known=False)
    assert check_recipients([stranger]).unfamiliar == ["new@inside.example"]


def test_each_reason_to_confirm_is_given():
    outsider = person("kai@outside.example", inside=False, known=False)
    reasons = check_recipients([outsider]).reasons
    assert reasons == [
        "someone outside the organisation",
        "an address not written to before",
    ]


def test_nothing_to_confirm_gives_no_reasons():
    assert check_recipients([person("ada@inside.example")]).reasons == []


def test_the_same_address_twice_is_counted_once():
    twice = [person("ada@inside.example"), person("ada@inside.example")]
    assert check_recipients(twice).reaches == 1


def test_a_message_to_nobody_is_refused():
    with pytest.raises(ValueError):
        check_recipients([])


def test_a_recipient_reaching_nobody_is_refused():
    with pytest.raises(ValueError):
        person("all@inside.example", is_list=True, reaches=0)
