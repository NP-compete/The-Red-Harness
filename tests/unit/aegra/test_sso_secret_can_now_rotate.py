"""One secret doing two jobs — and the split that ended it."""

from __future__ import annotations

import inspect

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


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for name in (
        "SSO_CLIENT_SECRET",
        "TOKEN_SEALING_SECRET",
        "TOKEN_SEALING_SECRET_PREVIOUS",
    ):
        monkeypatch.delenv(name, raising=False)
    yield


class TestTheTwoJobsAreSeparateNow:
    def test_the_seal_can_have_its_own_secret(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        assert sealing_secret() == DEDICATED

    def test_rotating_the_sign_on_secret_loses_nothing(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        sealed = encrypt_token("a-refresh-token", sealing_secret())

        monkeypatch.setenv("SSO_CLIENT_SECRET", "rotated")
        assert open_sealed_token(sealed) == "a-refresh-token"


class TestThereIsSomethingToFallBackOn:
    """The absence this file used to record."""

    def test_more_than_one_generation_is_offered(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        assert len(sealing_secrets()) > 1

    def test_the_low_level_pair_is_still_single_key(self):
        assert list(inspect.signature(decrypt_token).parameters) == [
            "encrypted",
            "secret",
        ]


class TestTheSplitCannotQuietlyComeUndone:
    def test_a_deployment_that_sets_nothing_still_uses_the_sign_on_secret(
        self, monkeypatch
    ):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        assert sealing_secret() == SSO

    def test_tokens_sealed_before_the_split_still_open_after_it(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        sealed_before = encrypt_token("a-refresh-token", SSO)

        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        assert open_sealed_token(sealed_before) == "a-refresh-token"

    def test_the_sign_on_secret_is_not_dropped_from_the_generations(self, monkeypatch):
        monkeypatch.setenv("SSO_CLIENT_SECRET", SSO)
        monkeypatch.setenv("TOKEN_SEALING_SECRET", DEDICATED)
        assert SSO in sealing_secrets()
