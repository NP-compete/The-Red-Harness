"""The vault source is reachable through the resolver."""

from __future__ import annotations

import pytest

from agent.src.security import secret_source
from agent.src.security.secret_source import SecretUnavailable, resolve


class TestTheReferenceReachesTheSource:
    def test_vault_is_no_longer_reported_as_unbuilt(self):
        assert "vault" not in secret_source.KNOWN_BUT_UNBUILT

    def test_the_resolver_knows_the_source(self):
        assert "vault" in secret_source.SOURCES

    def test_a_vault_reference_does_not_say_it_is_unbuilt(self, monkeypatch):
        monkeypatch.delenv("VAULT_ADDR", raising=False)
        with pytest.raises(SecretUnavailable) as raised:
            resolve("vault://team/agent#token")
        assert "not built yet" not in str(raised.value)


class TestADeploymentWithNoVault:
    def test_it_is_told_which_setting_is_missing(self, monkeypatch):
        monkeypatch.delenv("VAULT_ADDR", raising=False)
        with pytest.raises(SecretUnavailable) as raised:
            resolve("vault://team/agent#token")
        assert "VAULT_ADDR" in str(raised.value)

    def test_the_reference_is_named_too(self, monkeypatch):
        monkeypatch.delenv("VAULT_ADDR", raising=False)
        with pytest.raises(SecretUnavailable) as raised:
            resolve("vault://team/agent#token")
        assert "team/agent" in str(raised.value)


class TestABadReferenceIsCaughtBeforeAnythingIsContacted:
    def test_a_reference_with_no_field_fails_on_its_own_terms(self, monkeypatch):
        monkeypatch.setenv("VAULT_ADDR", "https://vault.example.test")
        with pytest.raises(SecretUnavailable) as raised:
            resolve("vault://team/agent")
        assert "field" in str(raised.value).lower()


class TestTheOtherSourcesAreUnchanged:
    def test_an_environment_reference_still_works(self, monkeypatch):
        monkeypatch.setenv("SOMETHING", "a-value")
        assert resolve("env:SOMETHING") == "a-value"

    def test_a_bare_name_still_means_the_environment(self, monkeypatch):
        monkeypatch.setenv("SOMETHING", "a-value")
        assert resolve("SOMETHING") == "a-value"

    def test_the_sources_still_unbuilt_still_say_so(self):
        with pytest.raises(SecretUnavailable) as raised:
            resolve("kms:some-key")
        assert "not built yet" in str(raised.value)
