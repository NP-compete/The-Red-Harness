"""Which networks people may reach the platform from."""

from __future__ import annotations

import pytest

from agent.src.security.network_allowlist import Allowlist, Outcome, check_source

OFFICE = Allowlist(
    ranges=("203.0.113.0/24", "2001:db8::/32"),
    enforced=True,
    break_glass_roles=("platform-admin",),
)


def test_an_address_inside_an_allowed_range_is_let_in():
    assert check_source("203.0.113.9", OFFICE, roles=()).outcome is Outcome.ALLOWED


def test_an_address_outside_every_range_is_refused():
    assert check_source("198.51.100.4", OFFICE, roles=()).outcome is Outcome.NOT_ALLOWED


def test_a_refusal_does_not_repeat_the_address_back():
    assert "198.51.100.4" not in check_source("198.51.100.4", OFFICE, roles=()).reason


def test_an_address_just_outside_the_range_is_refused():
    assert check_source("203.0.114.1", OFFICE, roles=()).permitted is False


def test_the_first_address_of_a_range_is_inside_it():
    assert check_source("203.0.113.0", OFFICE, roles=()).permitted is True


def test_the_last_address_of_a_range_is_inside_it():
    assert check_source("203.0.113.255", OFFICE, roles=()).permitted is True


def test_an_address_of_the_other_kind_is_handled_not_crashed():
    assert check_source("2001:db8::1", OFFICE, roles=()).permitted is True


def test_an_address_of_the_other_kind_outside_the_range_is_refused():
    assert check_source("2001:dead::1", OFFICE, roles=()).permitted is False


def test_something_that_is_not_an_address_is_refused():
    assert (
        check_source("not-an-address", OFFICE, roles=()).outcome is Outcome.UNREADABLE
    )


def test_an_empty_address_is_refused():
    assert check_source("", OFFICE, roles=()).permitted is False


def test_an_allowlist_that_is_not_enforced_lets_everyone_in():
    relaxed = Allowlist(
        ranges=("203.0.113.0/24",), enforced=False, break_glass_roles=()
    )
    assert check_source("198.51.100.4", relaxed, roles=()).permitted is True


def test_an_allowlist_that_is_not_enforced_still_reports_what_would_have_happened():
    relaxed = Allowlist(
        ranges=("203.0.113.0/24",), enforced=False, break_glass_roles=()
    )
    assert check_source("198.51.100.4", relaxed, roles=()).would_refuse is True


def test_an_administrator_may_get_in_from_anywhere():
    result = check_source("198.51.100.4", OFFICE, roles=("platform-admin",))
    assert result.outcome is Outcome.BREAK_GLASS


def test_getting_in_from_outside_is_recorded_as_exceptional():
    result = check_source("198.51.100.4", OFFICE, roles=("platform-admin",))
    assert result.exceptional is True


def test_an_administrator_inside_the_office_is_not_exceptional():
    assert (
        check_source("203.0.113.9", OFFICE, roles=("platform-admin",)).exceptional
        is False
    )


def test_an_ordinary_role_does_not_open_the_door():
    assert check_source("198.51.100.4", OFFICE, roles=("member",)).permitted is False


def test_an_empty_allowlist_that_is_enforced_lets_nobody_in():
    closed = Allowlist(ranges=(), enforced=True, break_glass_roles=())
    assert check_source("203.0.113.9", closed, roles=()).permitted is False


def test_a_malformed_range_is_refused_when_the_list_is_built():
    with pytest.raises(ValueError):
        Allowlist(ranges=("203.0.113.0/99",), enforced=True, break_glass_roles=())


def test_a_range_covering_the_whole_internet_is_refused():
    with pytest.raises(ValueError):
        Allowlist(ranges=("0.0.0.0/0",), enforced=True, break_glass_roles=())
