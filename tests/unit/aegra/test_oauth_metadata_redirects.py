"""Where an OAuth metadata probe is allowed to end up."""

from __future__ import annotations

import pytest

from agent.src.security.redirect_safety import follow


class TestAHopThatLeavesThePublicInternet:
    def test_a_redirect_to_link_local_is_refused(self):
        found = follow(
            "https://mcp.example.test/.well-known/oauth",
            next_hop=lambda _: "http://169.254.169.254/latest/meta-data/",
            allowed_hosts=["mcp.example.test"],
        )
        assert not found.ok
        assert "169.254.169.254" in found.reason

    def test_a_redirect_to_a_private_address_is_refused(self):
        found = follow(
            "https://mcp.example.test/.well-known/oauth",
            next_hop=lambda _: "http://10.0.0.5/admin",
            allowed_hosts=["mcp.example.test"],
        )
        assert not found.ok

    def test_a_redirect_to_localhost_is_refused(self):
        found = follow(
            "https://mcp.example.test/.well-known/oauth",
            next_hop=lambda _: "http://127.0.0.1:8080/",
            allowed_hosts=["mcp.example.test"],
        )
        assert not found.ok


class TestTheOrdinaryCaseStillWorks:
    def test_a_redirect_to_another_public_host_is_followed(self):
        hops = iter(["https://issuer.example.test/.well-known/oauth", None])

        found = follow(
            "https://mcp.example.test/.well-known/oauth",
            next_hop=lambda _: next(hops),
            allowed_hosts=["mcp.example.test", "issuer.example.test"],
        )
        assert found.ok
        assert found.final == "https://issuer.example.test/.well-known/oauth"

    def test_no_redirect_at_all_is_fine(self):
        found = follow(
            "https://mcp.example.test/.well-known/oauth",
            next_hop=lambda _: None,
            allowed_hosts=["mcp.example.test"],
        )
        assert found.ok
        assert found.final == "https://mcp.example.test/.well-known/oauth"


class TestItCannotBeStrungAlong:
    def test_a_loop_is_refused(self):
        found = follow(
            "https://a.example.test/x",
            next_hop=lambda _: "https://a.example.test/x",
            allowed_hosts=["a.example.test"],
        )
        assert not found.ok
        assert "loop" in found.reason

    def test_an_endless_chain_stops(self):
        count = iter(range(100))
        found = follow(
            "https://a.example.test/0",
            next_hop=lambda _: f"https://a.example.test/{next(count)}",
            allowed_hosts=["a.example.test"],
            max_hops=3,
        )
        assert not found.ok


class TestTheProbeUsesIt:
    """The check is no use beside the fetch; it has to be in it."""

    def test_the_metadata_fetch_does_not_follow_redirects_itself(self):
        import inspect

        from agent.aegra import mcp_oauth_handlers

        source = inspect.getsource(mcp_oauth_handlers)
        code = "\n".join(
            line for line in source.splitlines() if not line.strip().startswith("#")
        )
        assert "follow_redirects=True" not in code

    def test_it_checks_each_hop_itself(self):
        import inspect

        from agent.aegra import mcp_oauth_handlers

        source = inspect.getsource(mcp_oauth_handlers)
        assert "check_url" in source
        assert "follow_redirects=False" in source


class TestTheCheckCanFail:
    @pytest.mark.parametrize(
        "somewhere_internal",
        [
            "http://169.254.169.254/",
            "http://10.1.2.3/",
            "http://192.168.0.1/",
            "http://[::1]/",
        ],
    )
    def test_each_internal_destination_is_caught(self, somewhere_internal):
        found = follow(
            "https://mcp.example.test/x",
            next_hop=lambda _: somewhere_internal,
            allowed_hosts=["mcp.example.test"],
        )
        assert not found.ok, f"{somewhere_internal} was allowed"
