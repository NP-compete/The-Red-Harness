"""Passing a conversation to a colleague."""

from __future__ import annotations

import pytest

from agent.src.security.handoff import plan_handoff


def plan(used=("tracker", "docs"), receiver_has=("docs",), **kwargs):
    return plan_handoff(
        servers_used=list(used),
        receiver_connections=list(receiver_has),
        from_subject=kwargs.get("from_subject", "a@example.com"),
        to_subject=kwargs.get("to_subject", "b@example.com"),
    )


def test_the_conversation_changes_owner():
    assert plan().new_owner == "b@example.com"


def test_it_says_what_the_receiver_must_connect():
    assert plan().needs_connecting == ("tracker",)


def test_it_says_what_the_receiver_already_has():
    assert plan().already_connected == ("docs",)


def test_a_receiver_with_everything_needs_nothing():
    assert plan(receiver_has=("tracker", "docs")).needs_connecting == ()


def test_a_receiver_with_nothing_is_told_about_everything():
    assert plan(receiver_has=()).needs_connecting == ("docs", "tracker")


def test_no_credential_travels_with_the_conversation():
    assert not any(
        hasattr(plan(), field) for field in ("token", "credentials", "inherited_access")
    )


def test_handing_to_yourself_is_refused():
    with pytest.raises(ValueError):
        plan(to_subject="a@example.com")


def test_a_conversation_that_used_nothing_hands_over_cleanly():
    handoff = plan(used=(), receiver_has=())
    assert handoff.needs_connecting == ()
    assert handoff.already_connected == ()


def test_the_warning_is_present_whenever_something_must_be_connected():
    assert "connect" in plan().warning.lower()


def test_there_is_no_warning_when_nothing_is_missing():
    assert plan(receiver_has=("tracker", "docs")).warning == ""


def test_servers_are_reported_in_a_stable_order():
    assert plan(used=("z", "a", "m"), receiver_has=()).needs_connecting == (
        "a",
        "m",
        "z",
    )


def test_a_server_used_twice_is_mentioned_once():
    assert plan(used=("tracker", "tracker"), receiver_has=()).needs_connecting == (
        "tracker",
    )
