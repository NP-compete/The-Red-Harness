"""The token encryption key may live somewhere other than the pod."""

from __future__ import annotations

import pytest

from agent.aegra.mcp_crypto import McpKeyMissingError, _parse_fernet_key


class TestARawKeyStillWorks:
    def test_it_is_returned_unchanged(self, monkeypatch):
        monkeypatch.setenv("A_KEY", "jUmEn3Gu_5JC1zcyOdtS_6NJQ0khIYCZiGLcnN264Xk=")
        assert (
            _parse_fernet_key("A_KEY") == "jUmEn3Gu_5JC1zcyOdtS_6NJQ0khIYCZiGLcnN264Xk="
        )

    def test_surrounding_space_is_still_trimmed(self, monkeypatch):
        monkeypatch.setenv("A_KEY", "  a-key-value  ")
        assert _parse_fernet_key("A_KEY") == "a-key-value"


class TestAReferenceIsFollowed:
    def test_a_value_naming_a_source_is_resolved(self, monkeypatch):
        monkeypatch.setenv("ELSEWHERE", "the-real-key")
        monkeypatch.setenv("A_KEY", "env:ELSEWHERE")
        assert _parse_fernet_key("A_KEY") == "the-real-key"

    def test_a_reference_to_a_source_that_is_not_built_says_which(self, monkeypatch):
        monkeypatch.setenv("A_KEY", "vault:secret/data/fernet")
        with pytest.raises(McpKeyMissingError, match="vault"):
            _parse_fernet_key("A_KEY")

    def test_a_reference_that_resolves_to_nothing_is_a_missing_key(self, monkeypatch):
        monkeypatch.delenv("ELSEWHERE", raising=False)
        monkeypatch.setenv("A_KEY", "env:ELSEWHERE")
        with pytest.raises(McpKeyMissingError):
            _parse_fernet_key("A_KEY")

    def test_the_complaint_names_the_reference_not_the_value(self, monkeypatch):
        monkeypatch.setenv("ELSEWHERE", "the-real-key")
        monkeypatch.setenv("A_KEY", "env:ELSEWHERE")
        monkeypatch.delenv("ELSEWHERE")
        with pytest.raises(McpKeyMissingError) as refused:
            _parse_fernet_key("A_KEY")
        assert "the-real-key" not in str(refused.value)


class TestTheRefusalIsUnchanged:
    def test_an_unset_variable_still_stops_the_agent(self, monkeypatch):
        monkeypatch.delenv("A_KEY", raising=False)
        with pytest.raises(McpKeyMissingError):
            _parse_fernet_key("A_KEY")

    def test_the_complaint_still_names_the_variable(self, monkeypatch):
        monkeypatch.delenv("A_KEY", raising=False)
        with pytest.raises(McpKeyMissingError, match="A_KEY"):
            _parse_fernet_key("A_KEY")

    def test_an_empty_variable_is_still_missing(self, monkeypatch):
        monkeypatch.setenv("A_KEY", "   ")
        with pytest.raises(McpKeyMissingError):
            _parse_fernet_key("A_KEY")


class TestTellingTheTwoApart:
    def test_a_generated_key_is_never_read_as_a_reference(self):
        from cryptography.fernet import Fernet

        for _ in range(20):
            assert ":" not in Fernet.generate_key().decode()
