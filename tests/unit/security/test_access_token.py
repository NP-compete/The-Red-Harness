"""Tokens people create to call the platform from their own code."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agent.src.security.access_token import Refusal, Request, Token, issue, verify

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


def request(**kwargs) -> Request:
    defaults = {
        "owner": "ana",
        "name": "nightly export",
        "scopes": ("runs.read",),
        "owner_scopes": ("runs.read", "runs.write"),
        "lifetime": timedelta(days=30),
    }
    defaults.update(kwargs)
    return Request(**defaults)


def test_a_token_is_issued_with_a_secret():
    issued = issue(request(), now=NOW)
    assert issued.secret != ""


def test_the_secret_is_long_enough_to_be_worth_having():
    assert len(issue(request(), now=NOW).secret) >= 32


def test_two_tokens_never_share_a_secret():
    assert issue(request(), now=NOW).secret != issue(request(), now=NOW).secret


def test_the_stored_token_does_not_contain_the_secret():
    issued = issue(request(), now=NOW)
    assert issued.secret not in str(issued.token.__dict__)


def test_the_token_shows_a_hint_so_it_can_be_recognised_later():
    issued = issue(request(), now=NOW)
    assert issued.token.hint and issued.token.hint in issued.secret


def test_the_hint_is_too_short_to_be_useful_to_anyone_else():
    assert len(issue(request(), now=NOW).token.hint) <= 6


def test_a_token_cannot_be_given_a_scope_its_owner_lacks():
    with pytest.raises(ValueError):
        issue(request(scopes=("admin.everything",)), now=NOW)


def test_a_token_may_hold_fewer_scopes_than_its_owner():
    issued = issue(request(scopes=("runs.read",)), now=NOW)
    assert issued.token.scopes == ("runs.read",)


def test_a_token_with_no_scopes_is_refused():
    with pytest.raises(ValueError):
        issue(request(scopes=()), now=NOW)


def test_a_token_expires():
    issued = issue(request(), now=NOW)
    assert issued.token.expires_at == NOW + timedelta(days=30)


def test_a_token_that_never_expires_is_refused():
    with pytest.raises(ValueError):
        issue(request(lifetime=None), now=NOW)


def test_a_lifetime_beyond_the_ceiling_is_refused():
    with pytest.raises(ValueError):
        issue(request(lifetime=timedelta(days=400)), now=NOW)


def test_a_valid_token_verifies():
    issued = issue(request(), now=NOW)
    assert (
        verify(issued.secret, issued.token, need="runs.read", now=NOW).permitted is True
    )


def test_a_wrong_secret_does_not_verify():
    issued = issue(request(), now=NOW)
    assert (
        verify("not-the-secret", issued.token, need="runs.read", now=NOW).permitted
        is False
    )


def test_an_expired_token_does_not_verify():
    issued = issue(request(), now=NOW)
    later = NOW + timedelta(days=31)
    assert (
        verify(issued.secret, issued.token, need="runs.read", now=later).refusal
        is Refusal.EXPIRED
    )


def test_a_revoked_token_does_not_verify():
    issued = issue(request(), now=NOW)
    revoked = Token(**{**issued.token.__dict__, "revoked_at": NOW})
    assert (
        verify(issued.secret, revoked, need="runs.read", now=NOW).refusal
        is Refusal.REVOKED
    )


def test_a_token_without_the_needed_scope_does_not_verify():
    issued = issue(request(), now=NOW)
    assert (
        verify(issued.secret, issued.token, need="runs.write", now=NOW).refusal
        is Refusal.SCOPE_MISSING
    )


def test_a_failed_verification_says_nothing_about_the_secret():
    issued = issue(request(), now=NOW)
    result = verify("wrong", issued.token, need="runs.read", now=NOW)
    assert issued.token.hint not in result.reason


def test_a_token_without_a_name_is_refused():
    with pytest.raises(ValueError):
        issue(request(name="  "), now=NOW)
