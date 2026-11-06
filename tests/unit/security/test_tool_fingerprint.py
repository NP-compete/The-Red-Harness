"""Noticing when a tool is no longer the tool that was approved."""

from __future__ import annotations

import pytest

from agent.src.security.tool_fingerprint import (
    Change,
    ToolShape,
    compare,
    fingerprint,
)


def shape(**kwargs) -> ToolShape:
    defaults = {
        "name": "send-email",
        "description": "Send an email to a colleague",
        "parameters": {"to": "string", "body": "string"},
        "required": ("to",),
        "server": "mail",
    }
    defaults.update(kwargs)
    return ToolShape(**defaults)


def test_the_same_tool_has_the_same_fingerprint():
    assert fingerprint(shape()) == fingerprint(shape())


def test_parameter_order_does_not_change_the_fingerprint():
    reordered = shape(parameters={"body": "string", "to": "string"})
    assert fingerprint(reordered) == fingerprint(shape())


def test_a_new_parameter_changes_the_fingerprint():
    grown = shape(parameters={"to": "string", "body": "string", "bcc": "string"})
    assert fingerprint(grown) != fingerprint(shape())


def test_a_changed_description_changes_the_fingerprint():
    assert fingerprint(shape(description="Send an email to anyone")) != fingerprint(
        shape()
    )


def test_an_unchanged_tool_reports_no_change():
    assert compare(shape(), shape()).changes == ()


def test_an_unchanged_tool_needs_no_fresh_approval():
    assert compare(shape(), shape()).needs_reapproval is False


def test_a_new_parameter_is_reported():
    grown = shape(parameters={"to": "string", "body": "string", "bcc": "string"})
    assert Change.PARAMETER_ADDED in compare(shape(), grown).changes


def test_a_removed_parameter_is_reported():
    shrunk = shape(parameters={"to": "string"})
    assert Change.PARAMETER_REMOVED in compare(shape(), shrunk).changes


def test_a_retyped_parameter_is_reported():
    retyped = shape(parameters={"to": "array", "body": "string"})
    assert Change.PARAMETER_RETYPED in compare(shape(), retyped).changes


def test_a_newly_required_parameter_is_reported():
    stricter = shape(required=("to", "body"))
    assert Change.REQUIREMENT_CHANGED in compare(shape(), stricter).changes


def test_a_rewritten_description_is_reported():
    assert (
        Change.DESCRIPTION_CHANGED
        in compare(shape(), shape(description="Send anything")).changes
    )


def test_a_tool_that_moved_server_is_reported():
    assert Change.SERVER_CHANGED in compare(shape(), shape(server="relay")).changes


def test_a_tool_that_moved_server_needs_fresh_approval():
    assert compare(shape(), shape(server="relay")).needs_reapproval is True


def test_a_new_parameter_needs_fresh_approval():
    grown = shape(parameters={"to": "string", "body": "string", "bcc": "string"})
    assert compare(shape(), grown).needs_reapproval is True


def test_a_rewritten_description_needs_fresh_approval():
    assert compare(shape(), shape(description="Send anything")).needs_reapproval is True


def test_a_removed_parameter_does_not_need_fresh_approval():
    shrunk = shape(parameters={"to": "string"})
    assert compare(shape(), shrunk).needs_reapproval is False


def test_the_change_is_explained_in_words():
    grown = shape(parameters={"to": "string", "body": "string", "bcc": "string"})
    assert "bcc" in compare(shape(), grown).summary


def test_comparing_two_different_tools_is_refused():
    with pytest.raises(ValueError):
        compare(shape(), shape(name="delete-email"))


def test_a_tool_without_a_name_is_refused():
    with pytest.raises(ValueError):
        shape(name=" ")
