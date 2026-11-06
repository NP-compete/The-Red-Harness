"""An icon URL is an outbound fetch like any other."""

from __future__ import annotations

import pytest

from agent.aegra.mcp_routes import fetch_icon


def _followed(url, *, hops):
    """Walk the chain the handler would walk, synchronously."""
    import asyncio

    class _Reply:
        def __init__(self, where):
            self.where = where
            self.is_redirect = where is not None
            self.headers = {"location": where or "", "content-type": "image/png"}
            self.status_code = 200
            self.content = b"x"

    asked: list[str] = []

    class _Client:
        async def get(self, url, headers=None):
            asked.append(str(url))
            return _Reply(hops(str(url)))

    found = asyncio.run(fetch_icon(_Client(), url))
    return asked[-1] if found else None


class TestWhatIsAllowed:
    def test_the_configured_address_itself(self):
        found = _followed("https://cdn.example.com/icon.png", hops=lambda _u: None)
        assert found == "https://cdn.example.com/icon.png"

    def test_a_redirect_within_the_same_host(self):
        hops = {
            "https://cdn.example.com/icon.png": "https://cdn.example.com/v2/icon.png"
        }
        found = _followed(
            "https://cdn.example.com/icon.png", hops=lambda u: hops.get(u)
        )
        assert found == "https://cdn.example.com/v2/icon.png"


class TestWhatIsRefused:
    def test_a_redirect_to_another_host(self):
        hops = {"https://cdn.example.com/icon.png": "https://elsewhere.test/icon.png"}
        assert (
            _followed("https://cdn.example.com/icon.png", hops=lambda u: hops.get(u))
            is None
        )

    def test_a_redirect_into_the_cluster(self):
        hops = {
            "https://cdn.example.com/icon.png": "https://169.254.169.254/latest/meta-data/"
        }
        assert (
            _followed("https://cdn.example.com/icon.png", hops=lambda u: hops.get(u))
            is None
        )

    def test_a_redirect_to_loopback(self):
        hops = {"https://cdn.example.com/icon.png": "https://127.0.0.1/admin"}
        assert (
            _followed("https://cdn.example.com/icon.png", hops=lambda u: hops.get(u))
            is None
        )

    def test_a_redirect_that_drops_to_plain_http(self):
        hops = {"https://cdn.example.com/icon.png": "http://cdn.example.com/icon.png"}
        assert (
            _followed("https://cdn.example.com/icon.png", hops=lambda u: hops.get(u))
            is None
        )

    def test_an_address_that_was_never_https(self):
        assert (
            _followed("http://cdn.example.com/icon.png", hops=lambda _u: None) is None
        )

    def test_an_address_carrying_credentials(self):
        assert (
            _followed("https://user:pw@cdn.example.com/i.png", hops=lambda _u: None)
            is None
        )

    def test_a_redirect_loop(self):
        hops = {
            "https://cdn.example.com/a": "https://cdn.example.com/b",
            "https://cdn.example.com/b": "https://cdn.example.com/a",
        }
        assert (
            _followed("https://cdn.example.com/a", hops=lambda u: hops.get(u)) is None
        )

    def test_a_chain_that_never_ends(self):
        count = {"n": 0}

        def _hop(_url: str) -> str:
            count["n"] += 1
            return f"https://cdn.example.com/{count['n']}"

        assert _followed("https://cdn.example.com/0", hops=_hop) is None

    @pytest.mark.parametrize("url", ["", "   ", "not a url", "ftp://cdn.example.com/i"])
    def test_something_that_is_not_an_address(self, url):
        assert _followed(url, hops=lambda _u: None) is None


class TestTheRouteUsesIt:
    def test_the_icon_handler_checks_before_fetching(self):
        import inspect

        from agent.aegra import mcp_routes

        source = inspect.getsource(mcp_routes.mcp_icon)
        assert "fetch_icon" in source

    def test_it_no_longer_follows_redirects_on_its_own(self):
        import inspect

        from agent.aegra import mcp_routes

        icon = inspect.getsource(mcp_routes.mcp_icon)
        code = "\n".join(
            line for line in icon.splitlines() if not line.strip().startswith("#")
        )
        assert "follow_redirects=False" in code
        assert "follow_redirects=True" not in code
