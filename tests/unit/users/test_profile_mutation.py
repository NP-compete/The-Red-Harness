"""E9-T2. What the mutation surface accepts, refuses, and records."""

from __future__ import annotations

import pytest

from agent.src.users import authorization
from agent.src.users.profiles import MAX_FIELD_CHARS, ProfileError, validate


class TestValidate:
    def test_a_known_field_passes(self):
        assert validate({"display_name": "Ada"}) == {"display_name": "Ada"}

    def test_nothing_given_is_refused(self):
        with pytest.raises(ProfileError, match="no fields"):
            validate({})

    def test_membership_is_refused_as_a_shape_error(self):
        """400, not 403."""
        with pytest.raises(ProfileError) as exc:
            validate({"membership": "admins"})
        assert "identity provider" in str(exc.value)

    def test_an_unknown_field_names_itself(self):
        with pytest.raises(ProfileError, match="is_admin"):
            validate({"is_admin": "yes"})

    def test_a_non_string_is_refused(self):
        with pytest.raises(ProfileError, match="must be text"):
            validate({"display_name": {"nested": 1}})

    def test_an_oversized_value_is_refused(self):
        with pytest.raises(ProfileError, match="over the"):
            validate({"title": "x" * (MAX_FIELD_CHARS + 1)})

    def test_null_clears_a_field(self):
        """Clearing is a legitimate correction, not a missing value."""
        assert validate({"title": None}) == {"title": ""}


class TestAuthorization:
    @pytest.mark.asyncio
    async def test_an_unreachable_policy_refuses(self, monkeypatch):
        """Fails closed whatever `opa.fail_open` says."""
        monkeypatch.setattr(
            authorization,
            "decide",
            authorization.decide,
        )
        from agent.src.opa import config as opa_config

        monkeypatch.setattr(
            opa_config, "get_opa_url", lambda: "http://127.0.0.1:9/nope"
        )
        monkeypatch.setattr(opa_config, "get_opa_timeout", lambda: 0.2)

        verdict = await authorization.decide(
            actor_role="owners", target_role="users", field_class="profile"
        )
        assert verdict.allowed is False
        assert "could not be reached" in verdict.why

    @pytest.mark.asyncio
    async def test_every_class_is_asked_separately(self, monkeypatch):
        """All-or-nothing starts with asking all of them."""
        asked: list[str] = []

        async def fake(*, actor_role, target_role, field_class):
            asked.append(field_class)
            return authorization.Decision(True, [], field_class)

        monkeypatch.setattr(authorization, "decide", fake)
        out = await authorization.decide_all(
            actor_role="owners",
            target_role="users",
            field_classes=["entitlement", "profile", "profile"],
        )
        assert asked == ["entitlement", "profile"], "deduplicated and ordered"
        assert len(out) == 2

    def test_a_refusal_carries_a_reason_even_when_the_policy_gave_none(self):
        verdict = authorization.Decision(False, [], "profile")
        assert verdict.why == "refused by policy"
