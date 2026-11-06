"""A rotated key is in use on the next call, without a restart."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from agent.aegra import mcp_crypto


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("MCP_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("MCP_TOKEN_ENCRYPTION_KEY_PREVIOUS", raising=False)
    monkeypatch.delenv("SOMEWHERE_ELSE", raising=False)
    mcp_crypto.reset_mcp_crypto_cache()
    yield
    mcp_crypto.reset_mcp_crypto_cache()


def _key() -> str:
    return Fernet.generate_key().decode()


class TestAKeyHeldByReference:
    def test_the_new_key_is_used_for_writing(self, monkeypatch):
        first, second = _key(), _key()
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", "env:SOMEWHERE_ELSE")
        monkeypatch.setenv("SOMEWHERE_ELSE", first)
        mcp_crypto.encrypt_secret("before")

        monkeypatch.setenv("SOMEWHERE_ELSE", second)
        written = mcp_crypto.encrypt_secret("after")

        assert Fernet(second.encode()).decrypt(written.encode()) == b"after"

    def test_what_was_written_before_still_reads(self, monkeypatch):
        first, second = _key(), _key()
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", "env:SOMEWHERE_ELSE")
        monkeypatch.setenv("SOMEWHERE_ELSE", first)
        older = mcp_crypto.encrypt_secret("a refresh token")

        monkeypatch.setenv("SOMEWHERE_ELSE", second)
        assert mcp_crypto.decrypt_secret(older) == "a refresh token"

    def test_the_new_key_reads_its_own_writing(self, monkeypatch):
        first, second = _key(), _key()
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", "env:SOMEWHERE_ELSE")
        monkeypatch.setenv("SOMEWHERE_ELSE", first)
        mcp_crypto.encrypt_secret("before")

        monkeypatch.setenv("SOMEWHERE_ELSE", second)
        assert mcp_crypto.decrypt_secret(mcp_crypto.encrypt_secret("after")) == "after"

    def test_the_declared_previous_key_still_works_too(self, monkeypatch):
        old, new = _key(), _key()
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", old)
        sealed = mcp_crypto.encrypt_secret("older still")

        mcp_crypto.reset_mcp_crypto_cache()
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", "env:SOMEWHERE_ELSE")
        monkeypatch.setenv("SOMEWHERE_ELSE", new)
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY_PREVIOUS", old)
        assert mcp_crypto.decrypt_secret(sealed) == "older still"


class TestItDoesNotFallBackQuietly:
    def test_a_reference_that_stops_resolving_is_an_error(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", "env:SOMEWHERE_ELSE")
        monkeypatch.setenv("SOMEWHERE_ELSE", _key())
        mcp_crypto.encrypt_secret("before")

        monkeypatch.delenv("SOMEWHERE_ELSE")
        with pytest.raises(mcp_crypto.McpKeyMissingError):
            mcp_crypto.encrypt_secret("after")

    def test_the_complaint_names_the_variable_not_the_key(self, monkeypatch):
        secret = _key()
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", "env:SOMEWHERE_ELSE")
        monkeypatch.setenv("SOMEWHERE_ELSE", secret)
        mcp_crypto.encrypt_secret("before")

        monkeypatch.delenv("SOMEWHERE_ELSE")
        with pytest.raises(mcp_crypto.McpKeyMissingError) as raised:
            mcp_crypto.encrypt_secret("after")
        assert "MCP_TOKEN_ENCRYPTION_KEY" in str(raised.value)
        assert secret not in str(raised.value)

    def test_a_rotation_to_a_malformed_key_is_refused(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", "env:SOMEWHERE_ELSE")
        monkeypatch.setenv("SOMEWHERE_ELSE", _key())
        mcp_crypto.encrypt_secret("before")

        monkeypatch.setenv("SOMEWHERE_ELSE", "not-a-fernet-key")
        with pytest.raises(mcp_crypto.McpKeyMissingError):
            mcp_crypto.encrypt_secret("after")


class TestOnlyOneGenerationIsKept:
    def test_two_rotations_drop_the_oldest(self, monkeypatch):
        first, second, third = _key(), _key(), _key()
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", "env:SOMEWHERE_ELSE")
        monkeypatch.setenv("SOMEWHERE_ELSE", first)
        oldest = mcp_crypto.encrypt_secret("oldest")

        monkeypatch.setenv("SOMEWHERE_ELSE", second)
        middle = mcp_crypto.encrypt_secret("middle")

        monkeypatch.setenv("SOMEWHERE_ELSE", third)
        assert mcp_crypto.decrypt_secret(middle) == "middle"
        with pytest.raises(RuntimeError):
            mcp_crypto.decrypt_secret(oldest)


class TestALiteralKeyIsUnchanged:
    def test_it_still_round_trips(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", _key())
        assert mcp_crypto.decrypt_secret(mcp_crypto.encrypt_secret("x")) == "x"

    def test_it_is_read_once(self, monkeypatch):
        monkeypatch.setenv("MCP_TOKEN_ENCRYPTION_KEY", _key())
        mcp_crypto.encrypt_secret("x")

        reads = 0
        real = mcp_crypto._build_fernet

        def counting(env_var):
            nonlocal reads
            reads += 1
            return real(env_var)

        monkeypatch.setattr(mcp_crypto, "_build_fernet", counting)
        for _ in range(5):
            mcp_crypto.encrypt_secret("x")
        assert reads == 0

    def test_an_absent_key_still_stops_the_call(self, monkeypatch):
        monkeypatch.delenv("MCP_TOKEN_ENCRYPTION_KEY", raising=False)
        with pytest.raises(mcp_crypto.McpKeyMissingError):
            mcp_crypto.encrypt_secret("x")
