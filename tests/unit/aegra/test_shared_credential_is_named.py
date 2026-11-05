"""A server everyone reaches as the same caller should say so."""

from __future__ import annotations

from unittest.mock import patch

from agent.aegra.startup import warn_about_shared_credentials


def _said(servers):
    with patch("agent.aegra.startup.logger") as log:
        warn_about_shared_credentials(servers)
        return " ".join(str(call) for call in log.warning.call_args_list)


class TestWhenSomethingIsShared:
    def test_it_says_something(self):
        assert _said({"billing": {"enabled": True, "auth_mode": "api_key"}})

    def test_it_names_the_server(self):
        assert "billing" in _said(
            {"billing": {"enabled": True, "auth_mode": "api_key"}}
        )

    def test_it_says_what_that_means(self):
        said = _said({"billing": {"enabled": True, "auth_mode": "api_key"}}).lower()
        assert "same" in said or "everyone" in said or "shared" in said

    def test_several_are_named_in_one_line(self):
        said = _said(
            {
                "billing": {"enabled": True, "auth_mode": "api_key"},
                "ledger": {"enabled": True, "auth_mode": "api_key"},
            }
        )
        assert "billing" in said and "ledger" in said


class TestWhenNothingIs:
    def test_a_deployment_on_per_person_identity_is_told_nothing(self):
        assert _said({"wiki": {"enabled": True, "auth_mode": "sso"}}) == ""

    def test_the_default_mode_counts_as_per_person(self):
        assert _said({"wiki": {"enabled": True}}) == ""

    def test_a_server_that_is_off_is_not_warned_about(self):
        assert _said({"billing": {"enabled": False, "auth_mode": "api_key"}}) == ""

    def test_no_servers_at_all(self):
        assert _said({}) == ""


class TestItNeverStopsTheAgent:
    def test_a_shape_it_cannot_read_does_not_raise(self):
        warn_about_shared_credentials({"odd": "not a mapping"})

    def test_nothing_at_all_does_not_raise(self):
        warn_about_shared_credentials(None)


class TestItRunsAtStartup:
    def test_startup_calls_it(self):
        import inspect

        from agent.aegra import startup

        source = inspect.getsource(startup)
        calls = [
            line
            for line in source.splitlines()
            if "warn_about_shared_credentials(" in line
            and not line.strip().startswith("def ")
        ]
        assert calls
