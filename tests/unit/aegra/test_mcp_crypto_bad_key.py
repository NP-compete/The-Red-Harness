"""A key that is set but wrong must read as configuration, not a fault."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from agent.aegra.mcp_crypto import (
    McpKeyMissingError,
    encrypt_secret,
    reset_mcp_crypto_cache,
)

VALID = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_mcp_crypto_cache()
    yield
    reset_mcp_crypto_cache()


class TestAMalformedKey:
    @pytest.mark.parametrize(
        "bad",
        [
            "changeme12",
            VALID[:-4],
            "not base64 at all!",
            "",
        ],
    )
    def test_is_reported_as_configuration_not_an_internal_error(self, bad, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", bad)
        with pytest.raises(McpKeyMissingError):
            encrypt_secret("token")

    def test_the_message_says_what_to_do_without_leaking_the_key(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", "changeme12")
        with pytest.raises(McpKeyMissingError) as exc:
            encrypt_secret("token")
        msg = str(exc.value)
        assert "MCP_TOKEN_ENCRYPTION_KEY" in msg
        assert "Fernet.generate_key()" in msg
        assert "10 characters" in msg
        assert "changeme12" not in msg


class TestTheRotationKeyIsHeldToTheSameStandard:
    def test_a_bad_previous_key_is_configuration_too(self, monkeypatch):
        """Only reached when the primary cannot decrypt, so the"""
        other = Fernet.generate_key()
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", VALID)
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY_PREVIOUS", "changeme12")
        from agent.aegra.mcp_crypto import decrypt_secret

        with pytest.raises(McpKeyMissingError):
            decrypt_secret(Fernet(other).encrypt(b"x").decode())


class TestAValidKeyStillWorks:
    def test_round_trips(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", VALID)
        from agent.aegra.mcp_crypto import decrypt_secret

        assert decrypt_secret(encrypt_secret("hunter2")) == "hunter2"

    def test_an_absent_key_still_says_required(self, monkeypatch):
        monkeypatch.delenv("MCP_TOKEN_ENCRYPTION_KEY", raising=False)
        with pytest.raises(McpKeyMissingError, match="is required"):
            encrypt_secret("token")
