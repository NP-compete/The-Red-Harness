"""Reading a secret by reference, from wherever it is kept."""

from __future__ import annotations

import pytest

from agent.src.security.secret_source import (
    SecretUnavailable,
    from_environment,
    resolve,
)


class TestReadingFromTheEnvironment:
    def test_a_set_variable_resolves(self, monkeypatch):
        monkeypatch.setenv("A_SECRET", "s3cr3t-value")
        assert resolve("env:A_SECRET") == "s3cr3t-value"

    def test_a_bare_name_means_the_environment(self):
        import os

        os.environ["BARE_NAME"] = "value"
        try:
            assert resolve("BARE_NAME") == "value"
        finally:
            del os.environ["BARE_NAME"]

    def test_surrounding_space_is_ignored(self):
        import os

        os.environ["PADDED"] = "value"
        try:
            assert resolve("  env:PADDED  ") == "value"
        finally:
            del os.environ["PADDED"]


class TestWhenItIsNotThere:
    def test_it_raises_rather_than_returning_nothing(self, monkeypatch):
        monkeypatch.delenv("MISSING_ONE", raising=False)
        with pytest.raises(SecretUnavailable):
            resolve("env:MISSING_ONE")

    def test_the_complaint_names_the_reference(self, monkeypatch):
        monkeypatch.delenv("MISSING_ONE", raising=False)
        with pytest.raises(SecretUnavailable, match="MISSING_ONE"):
            resolve("env:MISSING_ONE")

    def test_an_empty_variable_counts_as_missing(self, monkeypatch):
        monkeypatch.setenv("EMPTY_ONE", "   ")
        with pytest.raises(SecretUnavailable):
            resolve("env:EMPTY_ONE")

    def test_a_source_nobody_implemented_says_which(self):
        with pytest.raises(SecretUnavailable, match="vault"):
            resolve("vault:secret/data/thing")

    def test_an_empty_reference_is_refused(self):
        with pytest.raises(SecretUnavailable):
            resolve("")


class TestTheValueNeverTravels:
    def test_the_error_does_not_carry_it(self, monkeypatch):
        monkeypatch.setenv("REJECTED", "   ")
        with pytest.raises(SecretUnavailable) as refused:
            resolve("env:REJECTED")
        assert "   " not in str(refused.value).replace("env:REJECTED", "")

    def test_nothing_is_logged_with_the_value_in_it(self, monkeypatch):
        from unittest.mock import patch

        monkeypatch.setenv("QUIET", "s3cr3t-value")
        with patch("agent.src.security.secret_source.logger") as log:
            resolve("env:QUIET")
        said = str(log.mock_calls)
        assert "s3cr3t-value" not in said

    def test_the_reference_is_recorded_though(self, monkeypatch):
        from unittest.mock import patch

        monkeypatch.setenv("QUIET", "s3cr3t-value")
        seen = []
        with patch(
            "agent.src.security.secret_source.emit_audit_event",
            side_effect=lambda kind, **details: seen.append(details),
        ):
            resolve("env:QUIET")
        assert seen and seen[0]["reference"] == "env:QUIET"


class TestNothingIsCached:
    def test_a_changed_value_is_seen_on_the_next_call(self, monkeypatch):
        monkeypatch.setenv("ROTATES", "first")
        assert resolve("env:ROTATES") == "first"
        monkeypatch.setenv("ROTATES", "second")
        assert resolve("env:ROTATES") == "second"

    def test_a_secret_removed_stops_resolving(self, monkeypatch):
        monkeypatch.setenv("GOES_AWAY", "here")
        assert resolve("env:GOES_AWAY") == "here"
        monkeypatch.delenv("GOES_AWAY")
        with pytest.raises(SecretUnavailable):
            resolve("env:GOES_AWAY")


class TestAddingASource:
    def test_the_environment_source_is_a_plain_function(self):
        assert from_environment("PATH") is not None

    def test_it_returns_nothing_for_something_unset(self):
        assert from_environment("DEFINITELY_NOT_SET_HERE") is None


class TestARealCallSiteUsesIt:
    """One interface is only one interface once something calls it."""

    @staticmethod
    def _resolved(cfg, monkeypatch=None):
        from agent.aegra.mcp_auth import resolve_oauth_client_secret

        return resolve_oauth_client_secret(cfg, "jira")

    def test_a_named_variable_still_resolves(self, monkeypatch):
        monkeypatch.setenv("JIRA_SECRET", "from-the-environment")
        assert (
            self._resolved({"client_secret_env": "JIRA_SECRET"})
            == "from-the-environment"
        )

    def test_an_unset_one_still_answers_nothing(self, monkeypatch):
        monkeypatch.delenv("JIRA_SECRET", raising=False)
        assert self._resolved({"client_secret_env": "JIRA_SECRET"}) is None

    def test_the_complaint_names_the_variable(self, monkeypatch, caplog):
        monkeypatch.delenv("JIRA_SECRET", raising=False)
        with caplog.at_level("ERROR"):
            self._resolved({"client_secret_env": "JIRA_SECRET"})
        assert "JIRA_SECRET" in caplog.text

    def test_it_goes_through_the_one_interface(self):
        import inspect

        from agent.aegra import mcp_auth

        source = inspect.getsource(mcp_auth.resolve_oauth_client_secret)
        assert "secret_source" in source or "resolve(" in source

    def test_a_reference_to_another_source_works_here_too(self, monkeypatch):
        monkeypatch.setenv("JIRA_SECRET", "from-the-environment")
        assert (
            self._resolved({"client_secret_env": "env:JIRA_SECRET"})
            == "from-the-environment"
        )

    def test_the_inline_fallback_is_untouched(self):
        assert self._resolved({"client_secret": "inline-value"}) == "inline-value"


class TestEverySiteThatNamesAReference:
    """Each place configuration chooses where a secret lives."""

    def test_a_channel_signing_secret_resolves(self, monkeypatch):
        from agent.src.channels.config import ChannelConfig

        monkeypatch.setenv("SLACK_SIGNING", "shhh")
        channel = ChannelConfig(type="slack", signing_secret_env="SLACK_SIGNING")
        assert channel.signing_secret == "shhh"

    def test_a_channel_secret_can_name_its_source(self, monkeypatch):
        from agent.src.channels.config import ChannelConfig

        monkeypatch.setenv("SLACK_SIGNING", "shhh")
        channel = ChannelConfig(type="slack", signing_secret_env="env:SLACK_SIGNING")
        assert channel.signing_secret == "shhh"

    def test_an_unset_channel_secret_is_still_nothing(self, monkeypatch):
        from agent.src.channels.config import ChannelConfig

        monkeypatch.delenv("SLACK_SIGNING", raising=False)
        channel = ChannelConfig(type="slack", signing_secret_env="SLACK_SIGNING")
        assert channel.signing_secret is None

    def test_the_channel_reads_it_at_use_time(self, monkeypatch):
        from agent.src.channels.config import ChannelConfig

        channel = ChannelConfig(type="slack", signing_secret_env="SLACK_SIGNING")
        monkeypatch.setenv("SLACK_SIGNING", "first")
        assert channel.signing_secret == "first"
        monkeypatch.setenv("SLACK_SIGNING", "second")
        assert channel.signing_secret == "second"

    def test_both_sites_go_through_the_one_resolver(self):
        import inspect

        from agent.aegra import mcp
        from agent.src.channels import config

        assert "secret_source" in inspect.getsource(config)
        assert "secret_source" in inspect.getsource(mcp)

    def test_a_derived_name_is_left_alone(self):
        import inspect

        from agent.src.infrastructure import subagents

        assert "ASYNC_SUBAGENT_" in inspect.getsource(subagents)


class TestResolutionsAreAudited:
    """A debug line is not a record."""

    @staticmethod
    def _emitted(reference, monkeypatch):
        from unittest.mock import patch

        monkeypatch.setenv("AUDITED", "s3cr3t-value")
        seen = []
        with patch(
            "agent.src.security.secret_source.emit_audit_event",
            side_effect=lambda kind, **details: seen.append((kind, details)),
        ):
            try:
                resolve(reference)
            except SecretUnavailable:
                pass
        return seen

    def test_a_resolution_is_recorded(self, monkeypatch):
        assert self._emitted("env:AUDITED", monkeypatch)

    def test_it_names_the_reference(self, monkeypatch):
        _kind, details = self._emitted("env:AUDITED", monkeypatch)[0]
        assert details["reference"] == "env:AUDITED"

    def test_it_says_which_source_answered(self, monkeypatch):
        _kind, details = self._emitted("env:AUDITED", monkeypatch)[0]
        assert details["source"] == "env"

    def test_it_never_carries_the_value(self, monkeypatch):
        seen = self._emitted("env:AUDITED", monkeypatch)
        assert "s3cr3t-value" not in str(seen)

    def test_the_event_says_what_kind_of_thing_happened(self, monkeypatch):
        kind, _details = self._emitted("env:AUDITED", monkeypatch)[0]
        assert "secret" in kind

    def test_a_failure_is_recorded_too(self, monkeypatch):
        monkeypatch.delenv("NOT_THERE", raising=False)
        seen = self._emitted("env:NOT_THERE", monkeypatch)
        assert seen and seen[0][1]["found"] is False

    def test_a_success_says_so(self, monkeypatch):
        _kind, details = self._emitted("env:AUDITED", monkeypatch)[0]
        assert details["found"] is True

    def test_an_audit_that_fails_does_not_cost_the_secret(self, monkeypatch):
        from unittest.mock import patch

        monkeypatch.setenv("AUDITED", "s3cr3t-value")
        with patch(
            "agent.src.security.secret_source.emit_audit_event",
            side_effect=RuntimeError("audit sink down"),
        ):
            assert resolve("env:AUDITED") == "s3cr3t-value"


class TestAVariableThatMayHoldAReference:
    """One rule for "read this variable, follow it if it points"."""

    def test_a_plain_value_comes_back_as_itself(self, monkeypatch):
        from agent.src.security.secret_source import from_variable

        monkeypatch.setenv("HOLDS_A_VALUE", "the-value")
        assert from_variable("HOLDS_A_VALUE") == "the-value"

    def test_a_reference_is_followed(self, monkeypatch):
        from agent.src.security.secret_source import from_variable

        monkeypatch.setenv("ELSEWHERE", "the-real-one")
        monkeypatch.setenv("HOLDS_A_REF", "env:ELSEWHERE")
        assert from_variable("HOLDS_A_REF") == "the-real-one"

    def test_an_unset_variable_is_nothing(self, monkeypatch):
        from agent.src.security.secret_source import from_variable

        monkeypatch.delenv("NOT_SET_AT_ALL", raising=False)
        assert from_variable("NOT_SET_AT_ALL") is None

    def test_a_reference_that_cannot_be_read_raises(self, monkeypatch):
        from agent.src.security.secret_source import from_variable

        monkeypatch.delenv("ELSEWHERE", raising=False)
        monkeypatch.setenv("HOLDS_A_REF", "env:ELSEWHERE")
        with pytest.raises(SecretUnavailable):
            from_variable("HOLDS_A_REF")

    def test_a_value_with_a_colon_in_it_is_still_tried_as_a_reference(
        self, monkeypatch
    ):
        from agent.src.security.secret_source import from_variable

        monkeypatch.setenv("ODD", "not-a-source:but-has-a-colon")
        with pytest.raises(SecretUnavailable):
            from_variable("ODD")

    def test_both_places_use_the_one_rule(self):
        import inspect

        from agent.aegra import mcp_crypto
        from agent.src.channels import dispatch

        assert "from_variable" in inspect.getsource(mcp_crypto)
        assert "from_variable" in inspect.getsource(dispatch)
