"""Following a redirect without losing the guarantees of the first check."""

from __future__ import annotations

import pytest

from agent.src.security.redirect_safety import follow

ALLOWED = ["example.com", "cdn.example.com"]


def hops(*urls: str):
    sequence = list(urls)

    def next_hop(url: str) -> str | None:
        return sequence.pop(0) if sequence else None

    return next_hop


def test_an_address_with_no_redirect_is_fetched():
    result = follow("https://example.com/a", next_hop=hops(), allowed_hosts=ALLOWED)
    assert result.ok is True
    assert result.final == "https://example.com/a"


def test_a_redirect_within_the_allowed_hosts_is_followed():
    result = follow(
        "https://example.com/a",
        next_hop=hops("https://cdn.example.com/b"),
        allowed_hosts=ALLOWED,
    )
    assert result.final == "https://cdn.example.com/b"


def test_a_redirect_off_the_allowed_hosts_is_refused():
    result = follow(
        "https://example.com/a",
        next_hop=hops("https://elsewhere.com/b"),
        allowed_hosts=ALLOWED,
    )
    assert result.ok is False
    assert "elsewhere.com" in result.reason


def test_a_redirect_to_an_internal_address_is_refused():
    result = follow(
        "https://example.com/a",
        next_hop=hops("https://169.254.169.254/latest"),
        allowed_hosts=ALLOWED + ["169.254.169.254"],
    )
    assert result.ok is False


def test_a_redirect_downgrading_to_plain_http_is_refused():
    result = follow(
        "https://example.com/a",
        next_hop=hops("http://example.com/b"),
        allowed_hosts=ALLOWED,
    )
    assert result.ok is False


def test_every_hop_is_recorded():
    result = follow(
        "https://example.com/a",
        next_hop=hops("https://cdn.example.com/b", "https://example.com/c"),
        allowed_hosts=ALLOWED,
    )
    assert result.chain == (
        "https://example.com/a",
        "https://cdn.example.com/b",
        "https://example.com/c",
    )


def test_too_many_hops_is_refused():
    endless = lambda url: "https://example.com/next"  # noqa: E731
    result = follow(
        "https://example.com/a", next_hop=endless, allowed_hosts=ALLOWED, max_hops=3
    )
    assert result.ok is False
    assert "redirect" in result.reason


def test_a_loop_is_caught_rather_than_running_to_the_limit():
    result = follow(
        "https://example.com/a",
        next_hop=lambda url: "https://example.com/a",
        allowed_hosts=ALLOWED,
        max_hops=50,
    )
    assert result.ok is False
    assert len(result.chain) < 50


def test_the_first_address_is_checked_too():
    result = follow("https://elsewhere.com/a", next_hop=hops(), allowed_hosts=ALLOWED)
    assert result.ok is False


@pytest.mark.parametrize("hops_allowed", [0, -1])
def test_a_nonsense_hop_limit_is_refused(hops_allowed):
    with pytest.raises(ValueError):
        follow(
            "https://example.com/a",
            next_hop=hops(),
            allowed_hosts=ALLOWED,
            max_hops=hops_allowed,
        )
