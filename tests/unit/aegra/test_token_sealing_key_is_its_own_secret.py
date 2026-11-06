"""The key that seals stored tokens is no longer the sign-on secret."""

from __future__ import annotations

import pytest

from agent.aegra.lifecycle import (
    decrypt_token,
    encrypt_token,
    open_sealed_token,
    sealing_secret,
    sealing_secrets,
)

SSO = "the-sign-on-secret"
DEDICATED = "the-dedicated-sealing-secret"
PREVIOUS = "the-secret-it-replaced"


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for name in (
        "SSO_CLIENT_SECRET",
        "TOKEN_SEALING_SECRET",
        "TOKEN_SEALING_SECRET_PREVIOUS",
    ):
        monkeypatch.delenv(name, raising=False)
    yield


class TestADeploymentThatChangesNothing:
    def test_it_still_seals_with_the_sign_on_secret(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        assert sealing_secret() == SSO

    def test_what_it_sealed_still_opens(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        sealed = encrypt_token("a-refresh-token", sealing_secret())
        assert open_sealed_token(sealed) == "a-refresh-token"


class TestADeploymentThatSetsTheDedicatedSecret:
    def test_it_seals_with_that_one(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        assert sealing_secret() == DEDICATED

    def test_tokens_sealed_before_the_switch_still_open(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        sealed_before = encrypt_token("a-refresh-token", SSO)

        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        assert open_sealed_token(sealed_before) == "a-refresh-token"

    def test_tokens_sealed_after_the_switch_open_too(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        sealed = encrypt_token("a-refresh-token", sealing_secret())
        assert open_sealed_token(sealed) == "a-refresh-token"


class TestRotatingTheDedicatedSecret:
    def test_what_the_previous_one_sealed_still_opens(self, monkeypatch):
        monkeypatch.setenv("TOKEN_SEALING_SECRET", PREVIOUS)
        sealed_before = encrypt_token("a-refresh-token", sealing_secret())

        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        monkeypatch.setenv("TOKEN_SEALING_SECRET_PREVIOUS", PREVIOUS)
        assert open_sealed_token(sealed_before) == "a-refresh-token"

    def test_a_key_two_rotations_ago_does_not(self, monkeypatch):
        monkeypatch.setenv("TOKEN_SEALING_SECRET", "two-rotations-ago")
        sealed_long_ago = encrypt_token("a-refresh-token", sealing_secret())

        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        monkeypatch.setenv("TOKEN_SEALING_SECRET_PREVIOUS", PREVIOUS)
        with pytest.raises(Exception):
            open_sealed_token(sealed_long_ago)


class TestTheSignOnSecretCanNowRotate:
    def test_rotating_it_does_not_lose_a_single_token(self, monkeypatch):
        """The whole point of the change, in one test."""
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        sealed = encrypt_token("a-refresh-token", sealing_secret())

        monkeypatch.setenv("SSO_CLIENT_SECRET", "a-freshly-rotated-sign-on-secret")
        assert open_sealed_token(sealed) == "a-refresh-token"

    def test_and_the_old_arrangement_still_would_have(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        sealed = encrypt_token("a-refresh-token", sealing_secret())

        monkeypatch.setenv("SSO_CLIENT_SECRET", "a-freshly-rotated-sign-on-secret")
        with pytest.raises(Exception):
            open_sealed_token(sealed)


@pytest.fixture
def _nothing_configured(monkeypatch):
    """No sign-on secret anywhere, including in settings."""
    from agent.src import settings as settings_module

    monkeypatch.setattr(settings_module.settings, "SSO_CLIENT_SECRET", None)
    yield


class TestWhichSecretsAreOffered:
    def test_the_current_one_comes_first(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        assert sealing_secrets()[0] == DEDICATED

    def test_the_sign_on_secret_stays_available_to_open_with(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        assert SSO in sealing_secrets()

    def test_a_deployment_with_nothing_set_offers_nothing(self, _nothing_configured):
        assert sealing_secrets() == []


class TestNothingIsSealedWithNothing:
    def test_an_unconfigured_deployment_does_not_seal_with_an_empty_key(
        self, _nothing_configured
    ):
        assert sealing_secret() == ""


class TestWhatThisPathActuallyIs:
    """Found while fixing it, and worth more than the fix."""

    def test_nothing_opens_the_stored_field_yet(self):
        import pathlib

        agent = pathlib.Path(__file__).resolve().parents[3] / "services" / "agent"
        readers = [
            path.name
            for path in agent.rglob("*.py")
            if "encrypted_refresh_token" in path.read_text(encoding="utf-8")
        ]
        assert readers == ["lifecycle.py"], (
            f"{readers} touch the sealed refresh token. If a reader was just "
            "added, open it with open_sealed_token so a rotated secret still "
            "works — decrypt_token with a single secret is the arrangement "
            "this file exists to describe."
        )

    def test_the_live_path_has_its_own_generations(self):
        from agent.aegra import mcp_crypto

        assert hasattr(mcp_crypto, "decrypt_secret")
        assert "_get_fernet_previous" in dir(mcp_crypto)


class TestTheOriginalBehaviourIsIntact:
    """The low-level pair is unchanged; only who chooses the key moved."""

    def test_a_secret_opens_what_it_sealed(self):
        sealed = encrypt_token("a-refresh-token", "some-secret")
        assert decrypt_token(sealed, "some-secret") == "a-refresh-token"

    def test_a_different_secret_does_not(self):
        sealed = encrypt_token("a-refresh-token", "some-secret")
        with pytest.raises(Exception):
            decrypt_token(sealed, "another-secret")
