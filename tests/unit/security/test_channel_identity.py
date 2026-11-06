"""Working out which person is behind a message from another system."""

from __future__ import annotations

import pytest

from agent.src.security.channel_identity import Inbound, resolve_sender

DIRECTORY = {
    "slack:U123": "someone@example.com",
    "email:someone@example.com": "someone@example.com",
}


def inbound(**kwargs) -> Inbound:
    defaults = {"channel": "slack", "external_id": "U123", "verified": True}
    defaults.update(kwargs)
    return Inbound(**defaults)


def test_a_known_sender_maps_to_their_account():
    assert (
        resolve_sender(inbound(), directory=DIRECTORY).subject == "someone@example.com"
    )


def test_the_same_person_from_another_channel_is_the_same_account():
    email = inbound(channel="email", external_id="someone@example.com")
    assert resolve_sender(email, directory=DIRECTORY).subject == "someone@example.com"


def test_an_unknown_sender_is_nobody():
    assert resolve_sender(inbound(external_id="U999"), directory=DIRECTORY) is None


def test_an_unverified_message_is_nobody_even_if_the_id_is_known():
    assert resolve_sender(inbound(verified=False), directory=DIRECTORY) is None


def test_an_unknown_channel_is_nobody():
    unknown = inbound(channel="carrier-pigeon")
    assert resolve_sender(unknown, directory=DIRECTORY) is None


def test_the_channel_it_arrived_on_is_remembered():
    assert resolve_sender(inbound(), directory=DIRECTORY).channel == "slack"


def test_a_resolved_sender_carries_no_elevated_rights():
    sender = resolve_sender(inbound(), directory=DIRECTORY)
    assert not any(hasattr(sender, field) for field in ("groups", "admin", "scopes"))


@pytest.mark.parametrize("external_id", ["", "   "])
def test_a_blank_identifier_is_nobody(external_id):
    assert resolve_sender(inbound(external_id=external_id), directory=DIRECTORY) is None


def test_identifiers_are_matched_exactly_rather_than_loosely():
    assert resolve_sender(inbound(external_id="u123"), directory=DIRECTORY) is None
