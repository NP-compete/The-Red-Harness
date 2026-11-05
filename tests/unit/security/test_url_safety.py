"""Deciding whether the agent may fetch a given address."""

from __future__ import annotations

import pytest

from agent.src.security.url_safety import check_url

ALLOWED = ["example.com", "docs.example.com"]


def check(url: str, **kwargs):
    kwargs.setdefault("allowed_hosts", ALLOWED)
    return check_url(url, **kwargs)


def test_an_allowed_host_is_permitted():
    assert check("https://example.com/page").ok is True


def test_a_host_not_on_the_list_is_refused():
    assert check("https://elsewhere.com/page").ok is False


def test_a_subdomain_is_not_the_same_host():
    assert check("https://evil.example.com/page").ok is False


def test_a_listed_subdomain_is_permitted():
    assert check("https://docs.example.com/page").ok is True


def test_a_lookalike_suffix_is_refused():
    assert check("https://notexample.com/page").ok is False


def test_plain_http_is_refused():
    result = check("http://example.com/page")
    assert result.ok is False
    assert "https" in result.reason


def test_a_non_web_scheme_is_refused():
    assert check("file:///etc/passwd").ok is False


def test_an_address_with_credentials_is_refused():
    assert check("https://user:pass@example.com/").ok is False


def test_a_loopback_address_is_refused():
    assert check("https://127.0.0.1/", allowed_hosts=["127.0.0.1"]).ok is False


def test_a_private_address_is_refused():
    assert check("https://10.0.0.5/", allowed_hosts=["10.0.0.5"]).ok is False


def test_the_cloud_metadata_address_is_refused():
    assert (
        check("https://169.254.169.254/latest/", allowed_hosts=["169.254.169.254"]).ok
        is False
    )


def test_the_host_is_reported_for_the_audit_trail():
    assert check("https://example.com/page").host == "example.com"


@pytest.mark.parametrize("url", ["", "   ", "not a url"])
def test_nonsense_is_refused_rather_than_guessed_at(url):
    assert check(url).ok is False
