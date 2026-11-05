"""Noticing when a connected server is not the one that was trusted."""

from __future__ import annotations

import pytest

from agent.src.security.server_trust import (
    Known,
    Seen,
    Trust,
    check_server,
)

KNOWN = Known(
    name="mail",
    url="https://mail.example.com/api",
    certificate_fingerprint="ab12cd34",
    tool_count=4,
)


def seen(**kwargs) -> Seen:
    defaults = {
        "name": "mail",
        "url": "https://mail.example.com/api",
        "certificate_fingerprint": "ab12cd34",
        "tool_count": 4,
    }
    defaults.update(kwargs)
    return Seen(**defaults)


def test_an_unchanged_server_is_trusted():
    assert check_server(seen(), known=KNOWN).trust is Trust.UNCHANGED


def test_an_unchanged_server_may_be_used():
    assert check_server(seen(), known=KNOWN).usable is True


def test_a_changed_address_is_not_trusted():
    moved = seen(url="https://mail.other.com/api")
    assert check_server(moved, known=KNOWN).trust is Trust.MOVED


def test_a_changed_address_may_not_be_used_until_confirmed():
    moved = seen(url="https://mail.other.com/api")
    assert check_server(moved, known=KNOWN).usable is False


def test_a_changed_address_names_both_addresses():
    moved = seen(url="https://mail.other.com/api")
    reason = check_server(moved, known=KNOWN).reason
    assert "mail.example.com" in reason and "mail.other.com" in reason


def test_a_changed_certificate_is_not_trusted():
    swapped = seen(certificate_fingerprint="ff99ff99")
    assert check_server(swapped, known=KNOWN).trust is Trust.CERTIFICATE_CHANGED


def test_a_changed_certificate_may_not_be_used():
    swapped = seen(certificate_fingerprint="ff99ff99")
    assert check_server(swapped, known=KNOWN).usable is False


def test_a_certificate_change_outranks_an_address_change():
    both = seen(url="https://mail.other.com/api", certificate_fingerprint="ff99ff99")
    assert check_server(both, known=KNOWN).trust is Trust.CERTIFICATE_CHANGED


def test_a_server_offering_new_tools_is_flagged():
    grown = seen(tool_count=7)
    assert check_server(grown, known=KNOWN).trust is Trust.TOOLS_CHANGED


def test_a_server_offering_new_tools_says_how_many():
    grown = seen(tool_count=7)
    assert "7" in check_server(grown, known=KNOWN).reason


def test_a_server_offering_fewer_tools_is_still_usable():
    shrunk = seen(tool_count=2)
    assert check_server(shrunk, known=KNOWN).usable is True


def test_a_server_offering_fewer_tools_is_still_reported():
    shrunk = seen(tool_count=2)
    assert check_server(shrunk, known=KNOWN).trust is Trust.TOOLS_CHANGED


def test_a_server_that_was_never_seen_before_is_new():
    assert check_server(seen(name="billing"), known=None).trust is Trust.UNKNOWN


def test_a_server_that_was_never_seen_before_may_not_be_used_silently():
    assert check_server(seen(name="billing"), known=None).usable is False


def test_comparing_against_a_different_server_is_refused():
    with pytest.raises(ValueError):
        check_server(seen(name="billing"), known=KNOWN)


def test_a_plain_http_server_is_never_trusted():
    insecure = seen(url="http://mail.example.com/api")
    assert check_server(insecure, known=KNOWN).usable is False


def test_a_plain_http_server_says_why():
    insecure = seen(url="http://mail.example.com/api")
    assert "encrypted" in check_server(insecure, known=KNOWN).reason


def test_a_server_without_a_name_is_refused():
    with pytest.raises(ValueError):
        seen(name=" ")
