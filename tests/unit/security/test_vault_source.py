"""Reading a secret out of a vault the organisation already runs."""

from __future__ import annotations

import pytest

from agent.src.security.secret_source import SecretUnavailable
from agent.src.security.vault_source import (
    VaultReference,
    needs_renewal,
    parse_reference,
    read_secret,
)


class TestTheReferenceSyntax:
    def test_a_path_and_a_field(self):
        found = parse_reference("vault://team/agent/tracker#token")
        assert found == VaultReference(path="team/agent/tracker", field="token")

    def test_a_deeper_path_is_kept_whole(self):
        found = parse_reference("vault://a/b/c/d/e#api_key")
        assert found.path == "a/b/c/d/e"
        assert found.field == "api_key"

    def test_the_scheme_may_be_left_off(self):
        assert parse_reference("//team/agent#token").path == "team/agent"

    def test_a_reference_with_no_field_is_refused(self):
        with pytest.raises(SecretUnavailable) as raised:
            parse_reference("vault://team/agent/tracker")
        assert "field" in str(raised.value).lower()

    def test_a_reference_with_no_path_is_refused(self):
        with pytest.raises(SecretUnavailable):
            parse_reference("vault://#token")

    def test_an_empty_reference_is_refused(self):
        with pytest.raises(SecretUnavailable):
            parse_reference("vault://")

    @pytest.mark.parametrize("escaping", ["../", "team/../../root", "a/./b"])
    def test_a_path_that_tries_to_climb_is_refused(self, escaping):
        with pytest.raises(SecretUnavailable):
            parse_reference(f"vault://{escaping}#token")


class TestTheVaultsOwnCredential:
    def test_it_comes_from_the_platform_identity(self):
        asked: dict = {}

        def login(identity: str) -> tuple[str, int]:
            asked["identity"] = identity
            return "a-vault-token", 3600

        def fetch(path, field, token):
            asked["token"] = token
            return "the-secret"

        found = read_secret(
            parse_reference("vault://team/agent#token"),
            platform_identity=lambda: "a-projected-service-account-token",
            login=login,
            fetch=fetch,
        )
        assert found == "the-secret"
        assert asked["identity"] == "a-projected-service-account-token"
        assert asked["token"] == "a-vault-token"

    def test_no_platform_identity_is_a_refusal_not_a_fallback(self):
        with pytest.raises(SecretUnavailable) as raised:
            read_secret(
                parse_reference("vault://team/agent#token"),
                platform_identity=lambda: None,
                login=lambda identity: ("t", 3600),
                fetch=lambda p, f, t: "the-secret",
            )
        said = str(raised.value).lower()
        assert "identity" in said or "platform" in said


class TestTheLease:
    def test_a_fresh_lease_is_not_renewed(self):
        assert not needs_renewal(lease_seconds=3600, age_seconds=10)

    def test_a_lease_near_its_end_is_renewed_before_it_expires(self):
        assert needs_renewal(lease_seconds=3600, age_seconds=3500)

    def test_an_expired_lease_is_renewed(self):
        assert needs_renewal(lease_seconds=3600, age_seconds=4000)

    def test_a_very_short_lease_still_gets_renewed_early(self):
        assert not needs_renewal(lease_seconds=10, age_seconds=1)
        assert needs_renewal(lease_seconds=10, age_seconds=9)

    def test_a_lease_that_never_expires_is_never_renewed(self):
        assert not needs_renewal(lease_seconds=0, age_seconds=10**6)


class TestNothingLeaksIntoAMessage:
    def test_a_missing_field_names_the_reference_not_the_contents(self):
        def fetch(path, field, token):
            return None

        with pytest.raises(SecretUnavailable) as raised:
            read_secret(
                parse_reference("vault://team/agent#token"),
                platform_identity=lambda: "identity",
                login=lambda identity: ("vault-token", 3600),
                fetch=fetch,
            )
        said = str(raised.value)
        assert "team/agent" in said
        assert "vault-token" not in said

    def test_a_vault_that_fails_does_not_quote_the_token(self):
        def login(identity):
            raise RuntimeError("boom with vault-token-abc in it")

        with pytest.raises(SecretUnavailable) as raised:
            read_secret(
                parse_reference("vault://team/agent#token"),
                platform_identity=lambda: "identity",
                login=login,
                fetch=lambda p, f, t: "x",
            )
        assert "vault-token-abc" not in str(raised.value)
        assert "team/agent" in str(raised.value)

    def test_the_platform_identity_is_never_quoted_either(self):
        def login(identity):
            raise RuntimeError("rejected")

        with pytest.raises(SecretUnavailable) as raised:
            read_secret(
                parse_reference("vault://team/agent#token"),
                platform_identity=lambda: "a-projected-service-account-token",
                login=login,
                fetch=lambda p, f, t: "x",
            )
        assert "a-projected-service-account-token" not in str(raised.value)


class TestItReadsOnlyWhatWasAsked:
    def test_only_the_named_field_is_requested(self):
        seen: dict = {}

        def fetch(path, field, token):
            seen["path"] = path
            seen["field"] = field
            return "the-secret"

        read_secret(
            parse_reference("vault://team/agent/tracker#api_key"),
            platform_identity=lambda: "identity",
            login=lambda identity: ("vault-token", 3600),
            fetch=fetch,
        )
        assert seen == {"path": "team/agent/tracker", "field": "api_key"}

    def test_a_blank_value_is_treated_as_missing(self):
        with pytest.raises(SecretUnavailable):
            read_secret(
                parse_reference("vault://team/agent#token"),
                platform_identity=lambda: "identity",
                login=lambda identity: ("vault-token", 3600),
                fetch=lambda p, f, t: "   ",
            )
