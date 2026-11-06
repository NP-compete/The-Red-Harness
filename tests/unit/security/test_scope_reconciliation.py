"""Noticing when a connection comes back with less access than it had."""

from __future__ import annotations

import pytest

from agent.src.security.scope_reconciliation import reconcile


def test_the_same_scopes_are_unchanged():
    result = reconcile(granted=["read", "write"], requested=["read", "write"])
    assert result.changed is False


def test_fewer_scopes_than_asked_for_is_a_narrowing():
    result = reconcile(granted=["read"], requested=["read", "write"])
    assert result.narrowed == ("write",)


def test_a_narrowing_is_reported_as_a_change():
    assert reconcile(granted=["read"], requested=["read", "write"]).changed is True


def test_more_scopes_than_asked_for_is_also_reported():
    result = reconcile(granted=["read", "write"], requested=["read"])
    assert result.widened == ("write",)


def test_a_widening_is_not_treated_as_an_error():
    assert reconcile(granted=["read", "write"], requested=["read"]).ok is True


def test_losing_a_scope_the_agent_depends_on_is_not_ok():
    result = reconcile(
        granted=["read"], requested=["read", "write"], required=["write"]
    )
    assert result.ok is False


def test_losing_an_optional_scope_is_still_ok():
    result = reconcile(granted=["read"], requested=["read", "write"], required=["read"])
    assert result.ok is True


def test_the_message_names_what_was_lost():
    result = reconcile(
        granted=["read"], requested=["read", "write"], required=["write"]
    )
    assert "write" in result.message


def test_an_unchanged_connection_has_no_message():
    assert reconcile(granted=["read"], requested=["read"]).message == ""


def test_scope_order_does_not_matter():
    assert (
        reconcile(granted=["write", "read"], requested=["read", "write"]).changed
        is False
    )


def test_duplicates_do_not_look_like_a_change():
    assert reconcile(granted=["read", "read"], requested=["read"]).changed is False


def test_a_connection_granting_nothing_is_not_ok():
    result = reconcile(granted=[], requested=["read"], required=["read"])
    assert result.ok is False


@pytest.mark.parametrize("requested", [[], ["  "]])
def test_a_request_for_nothing_is_refused(requested):
    with pytest.raises(ValueError):
        reconcile(granted=["read"], requested=requested)
